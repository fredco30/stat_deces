"""
ETL Utilities for French Mortality Data Application
Handles DuckDB operations, CSV import, data cleaning, and transformations.
"""

import duckdb
import pandas as pd
import os
from pathlib import Path
from typing import Tuple, Optional, List
import hashlib
import requests
import time
from contextlib import contextmanager


# Database configuration
DB_PATH = Path(__file__).parent / "mortality_data.duckdb"
GEOJSON_URL = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements.geojson"
GEOJSON_PATH = Path(__file__).parent / "departements.geojson"

# Population data files
POPULATION_DEPT_PATH = Path(__file__).parent / "population_dept.csv"
POPULATION_AGE_PATH = Path(__file__).parent / "population_age.csv"
POPULATION_COMPLETE_PATH = Path(__file__).parent / "population_complete.csv"


def get_connection(read_only: bool = False, max_retries: int = 3) -> duckdb.DuckDBPyConnection:
    """
    Get a DuckDB connection with retry logic.

    Args:
        read_only: If True, open in read-only mode (allows concurrent access)
        max_retries: Maximum number of retry attempts

    Returns:
        DuckDB connection
    """
    for attempt in range(max_retries):
        try:
            if read_only:
                # Read-only mode allows multiple concurrent connections
                return duckdb.connect(str(DB_PATH), read_only=True)
            else:
                # Normal read-write mode
                return duckdb.connect(str(DB_PATH))
        except Exception as e:
            if attempt < max_retries - 1:
                # Exponential backoff: wait 0.1s, 0.2s, 0.4s
                wait_time = 0.1 * (2 ** attempt)
                time.sleep(wait_time)
            else:
                # Last attempt failed, raise the exception
                raise


@contextmanager
def db_connection(read_only: bool = False):
    """
    Context manager for DuckDB connections.
    Ensures connections are properly closed even if an error occurs.

    Usage:
        with db_connection() as conn:
            result = conn.execute("SELECT ...").fetchall()
    """
    conn = None
    try:
        conn = get_connection(read_only=read_only)
        yield conn
    finally:
        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass  # Ignore errors during close


def reset_database() -> None:
    """Reset the database by dropping all tables. Use with caution!"""
    conn = get_connection()
    try:
        conn.execute("DROP TABLE IF EXISTS deces")
        conn.execute("DROP TABLE IF EXISTS import_logs")
        conn.execute("DROP SEQUENCE IF EXISTS import_logs_seq")
    except Exception:
        pass
    conn.close()


def check_and_migrate_database() -> bool:
    """Check if database needs migration and perform it if necessary."""
    conn = get_connection()
    needs_reset = False

    try:
        # Try to check the table structure
        result = conn.execute("SELECT * FROM deces LIMIT 0").description
        column_names = [col[0] for col in result] if result else []

        # Check if 'id' column exists (old structure)
        if 'id' in column_names:
            needs_reset = True

        # Check if hash_unique is the primary key
        if 'hash_unique' not in column_names:
            needs_reset = True

    except Exception:
        # Table doesn't exist, that's fine
        pass

    conn.close()

    if needs_reset:
        print("Migration de la base de données nécessaire...")
        reset_database()
        return True

    return False


def init_database() -> None:
    """Initialize the database with required tables."""
    # Check if migration is needed
    check_and_migrate_database()

    conn = get_connection()

    # Main deaths table with unique constraint to prevent duplicates
    # Note: In DuckDB, we don't need an explicit id column - hash_unique serves as unique identifier
    conn.execute("""
        CREATE TABLE IF NOT EXISTS deces (
            nomprenom VARCHAR,
            sexe INTEGER,
            datenaiss DATE,
            lieunaiss VARCHAR,
            commnaiss VARCHAR,
            paysnaiss VARCHAR,
            datedeces DATE,
            lieudeces VARCHAR,
            actedeces VARCHAR,
            -- Computed columns
            annee_deces INTEGER,
            mois_deces INTEGER,
            jour_deces INTEGER,
            age_deces DOUBLE,
            departement VARCHAR,
            -- Hash for deduplication (serves as unique identifier)
            hash_unique VARCHAR PRIMARY KEY
        )
    """)

    # Import tracking table
    conn.execute("""
        CREATE SEQUENCE IF NOT EXISTS import_logs_seq START 1
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS import_logs (
            id INTEGER DEFAULT nextval('import_logs_seq'),
            filename VARCHAR,
            import_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            rows_added INTEGER,
            rows_duplicates INTEGER,
            status VARCHAR
        )
    """)

    # Create indexes for performance
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deces_annee ON deces(annee_deces)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deces_mois ON deces(mois_deces)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deces_dept ON deces(departement)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deces_sexe ON deces(sexe)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_deces_date ON deces(datedeces)")

    conn.close()


def parse_date_insee(date_str: str) -> Optional[str]:
    """
    Parse INSEE date format (YYYYMMDD) to ISO format (YYYY-MM-DD).
    Returns None if invalid.
    """
    if not date_str or len(str(date_str)) < 8:
        return None

    date_str = str(date_str).strip()

    # Handle partial dates (e.g., year only or year-month only)
    if len(date_str) == 4:  # Year only
        return f"{date_str}-01-01"
    elif len(date_str) == 6:  # Year-month
        return f"{date_str[:4]}-{date_str[4:6]}-01"
    elif len(date_str) >= 8:
        year = date_str[:4]
        month = date_str[4:6]
        day = date_str[6:8]

        # Validate
        try:
            y, m, d = int(year), int(month), int(day)
            if 1800 <= y <= 2100 and 1 <= m <= 12 and 1 <= d <= 31:
                return f"{year}-{month}-{day}"
        except ValueError:
            pass

    return None


def extract_departement(lieu_deces: str) -> str:
    """
    Extract department code from lieu_deces.
    - 2 first chars for metropolitan France
    - 3 first chars for DOM-TOM (starting with 97)
    """
    if not lieu_deces:
        return "00"

    lieu = str(lieu_deces).strip()

    if len(lieu) < 2:
        return "00"

    # DOM-TOM departments start with 97
    if lieu.startswith("97") and len(lieu) >= 3:
        return lieu[:3]

    # Corsica: 2A and 2B
    if lieu.startswith("2A") or lieu.startswith("2B"):
        return lieu[:2]

    # Standard metropolitan departments
    return lieu[:2]


def compute_hash(row: dict) -> str:
    """
    Compute unique hash for deduplication.
    Uses: nomprenom + datenaiss + datedeces + lieudeces
    """
    key = f"{row.get('nomprenom', '')}{row.get('datenaiss', '')}{row.get('datedeces', '')}{row.get('lieudeces', '')}"
    return hashlib.md5(key.encode()).hexdigest()


def calculate_age(datenaiss: str, datedeces: str) -> Optional[float]:
    """Calculate age at death in years."""
    if not datenaiss or not datedeces:
        return None

    try:
        from datetime import datetime
        birth = datetime.strptime(datenaiss, "%Y-%m-%d")
        death = datetime.strptime(datedeces, "%Y-%m-%d")
        age = (death - birth).days / 365.25
        return round(age, 2) if age >= 0 else None
    except (ValueError, TypeError):
        return None


def process_csv_file(file_content: bytes, filename: str) -> Tuple[int, int, str]:
    """
    Process a CSV file and insert data into DuckDB.

    Args:
        file_content: Raw bytes of the CSV file
        filename: Original filename for logging

    Returns:
        Tuple of (rows_added, duplicates_ignored, status_message)
    """
    import io

    try:
        # Try different encodings
        content_str = None
        for encoding in ['utf-8', 'latin-1', 'cp1252']:
            try:
                content_str = file_content.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if content_str is None:
            return 0, 0, "Erreur: Impossible de décoder le fichier"

        # Read CSV with pandas
        df = pd.read_csv(
            io.StringIO(content_str),
            sep=';',
            dtype=str,
            on_bad_lines='skip'
        )

        # Normalize column names (lowercase, strip)
        df.columns = [col.lower().strip().replace('"', '') for col in df.columns]

        # Required columns check
        required_cols = ['nomprenom', 'sexe', 'datenaiss', 'datedeces', 'lieudeces']
        missing_cols = [col for col in required_cols if col not in df.columns]

        if missing_cols:
            return 0, 0, f"Colonnes manquantes: {', '.join(missing_cols)}"

        conn = get_connection()
        rows_added = 0
        duplicates = 0

        for _, row in df.iterrows():
            try:
                # Parse dates
                datenaiss_iso = parse_date_insee(row.get('datenaiss', ''))
                datedeces_iso = parse_date_insee(row.get('datedeces', ''))

                if not datedeces_iso:
                    continue  # Skip rows without valid death date

                # Extract components from death date
                annee_deces = int(datedeces_iso[:4])
                mois_deces = int(datedeces_iso[5:7])
                jour_deces = int(datedeces_iso[8:10])

                # Calculate age
                age_deces = calculate_age(datenaiss_iso, datedeces_iso)

                # Extract department
                departement = extract_departement(row.get('lieudeces', ''))

                # Compute deduplication hash
                hash_unique = compute_hash(row)

                # Parse sexe
                try:
                    sexe = int(str(row.get('sexe', '0')).strip())
                except ValueError:
                    sexe = 0

                # Insert with conflict handling (ignore duplicates)
                conn.execute("""
                    INSERT OR IGNORE INTO deces (
                        nomprenom, sexe, datenaiss, lieunaiss, commnaiss, paysnaiss,
                        datedeces, lieudeces, actedeces,
                        annee_deces, mois_deces, jour_deces, age_deces, departement,
                        hash_unique
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, [
                    str(row.get('nomprenom', '')),
                    sexe,
                    datenaiss_iso,
                    str(row.get('lieunaiss', '')),
                    str(row.get('commnaiss', '')),
                    str(row.get('paysnaiss', '')),
                    datedeces_iso,
                    str(row.get('lieudeces', '')),
                    str(row.get('actedeces', '')),
                    annee_deces,
                    mois_deces,
                    jour_deces,
                    age_deces,
                    departement,
                    hash_unique
                ])

                # Check if row was actually inserted
                if conn.fetchone() is None:
                    rows_added += 1
                else:
                    duplicates += 1

            except Exception as e:
                duplicates += 1
                continue

        # Log import
        conn.execute("""
            INSERT INTO import_logs (filename, rows_added, rows_duplicates, status)
            VALUES (?, ?, ?, ?)
        """, [filename, rows_added, duplicates, 'success'])

        conn.close()

        # Recount to get accurate numbers
        conn = get_connection()
        result = conn.execute("SELECT changes()").fetchone()
        conn.close()

        return rows_added, duplicates, f"Import réussi: {rows_added} lignes ajoutées, {duplicates} doublons ignorés"

    except Exception as e:
        return 0, 0, f"Erreur lors de l'import: {str(e)}"


def import_csv_batch(file_content: bytes, filename: str, progress_callback=None) -> Tuple[int, int, str]:
    """
    Ultra-fast batch import using native DuckDB SQL operations.
    Processes 700k+ rows in seconds instead of minutes.
    """
    import tempfile

    try:
        # Progress: Starting
        if progress_callback:
            try:
                progress_callback(0.05, 0)
            except TypeError:
                progress_callback(0.05)

        # Write to temp file for DuckDB to read directly
        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = tmp.name

        conn = get_connection()

        # Get count before import
        count_before = conn.execute("SELECT COUNT(*) FROM deces").fetchone()[0]

        # Progress: File written, starting DuckDB load
        if progress_callback:
            try:
                progress_callback(0.1, 0)
            except TypeError:
                progress_callback(0.1)

        # Create temporary table and load CSV directly with DuckDB (ultra-fast)
        try:
            # Drop temp table if exists
            conn.execute("DROP TABLE IF EXISTS temp_import")

            # Load CSV into temp table - DuckDB reads CSV at GB/s speed
            # Use quote='"' to handle quoted values properly
            conn.execute(f"""
                CREATE TEMP TABLE temp_import AS
                SELECT * FROM read_csv('{tmp_path}',
                    delim=';',
                    header=true,
                    ignore_errors=true,
                    all_varchar=true,
                    quote='"',
                    escape='"'
                )
            """)

            # Get row count
            total_rows = conn.execute("SELECT COUNT(*) FROM temp_import").fetchone()[0]

            # Get actual column names from the imported table
            columns_info = conn.execute("DESCRIBE temp_import").fetchall()
            actual_columns = [col[0].lower().strip().replace('"', '') for col in columns_info]

        except Exception as e:
            os.unlink(tmp_path)
            return 0, 0, f"Erreur lecture CSV: {str(e)}"

        # Clean up temp file
        os.unlink(tmp_path)

        # Progress: CSV loaded, starting transformation
        if progress_callback:
            try:
                progress_callback(0.3, total_rows)
            except TypeError:
                progress_callback(0.3)

        # Build dynamic column mapping based on actual columns
        # Expected columns: nomprenom, sexe, datenaiss, lieunaiss, commnaiss, paysnaiss, datedeces, lieudeces, actedeces
        def find_column(expected, actual_cols):
            """Find matching column name (handles quotes, case, etc.)"""
            expected_lower = expected.lower()
            for col in actual_cols:
                col_clean = col.lower().strip().replace('"', '')
                if col_clean == expected_lower:
                    return col
            return None

        # Get original column names from DuckDB
        orig_columns = [col[0] for col in columns_info]

        # Map expected columns to actual columns
        col_map = {}
        for expected in ['nomprenom', 'sexe', 'datenaiss', 'lieunaiss', 'commnaiss', 'paysnaiss', 'datedeces', 'lieudeces', 'actedeces']:
            for orig_col in orig_columns:
                if orig_col.lower().strip().replace('"', '') == expected:
                    # Use column name as-is if it already has quotes, otherwise add them
                    if orig_col.startswith('"') and orig_col.endswith('"'):
                        col_map[expected] = orig_col
                    else:
                        col_map[expected] = f'"{orig_col}"'
                    break
            if expected not in col_map:
                col_map[expected] = "''"  # Default empty string if column not found

        # Normalize column names using dynamic mapping
        conn.execute(f"""
            CREATE TEMP TABLE temp_normalized AS
            SELECT
                COALESCE({col_map.get('nomprenom', "''")}, '') as nomprenom,
                COALESCE({col_map.get('sexe', "'0'")}, '0') as sexe,
                COALESCE({col_map.get('datenaiss', "''")}, '') as datenaiss,
                COALESCE({col_map.get('lieunaiss', "''")}, '') as lieunaiss,
                COALESCE({col_map.get('commnaiss', "''")}, '') as commnaiss,
                COALESCE({col_map.get('paysnaiss', "''")}, '') as paysnaiss,
                COALESCE({col_map.get('datedeces', "''")}, '') as datedeces,
                COALESCE({col_map.get('lieudeces', "''")}, '') as lieudeces,
                COALESCE({col_map.get('actedeces', "''")}, '') as actedeces
            FROM temp_import
        """)

        # Progress: Normalized, starting SQL transformations
        if progress_callback:
            try:
                progress_callback(0.4, total_rows)
            except TypeError:
                progress_callback(0.4)

        # Create transformed table with all computed columns using pure SQL
        conn.execute("""
            CREATE TEMP TABLE temp_transformed AS
            SELECT
                nomprenom,
                TRY_CAST(NULLIF(TRIM(sexe), '') AS INTEGER) as sexe,
                -- Parse birth date (YYYYMMDD -> DATE)
                CASE
                    WHEN LENGTH(TRIM(datenaiss)) >= 8 THEN
                        TRY_CAST(
                            SUBSTR(datenaiss, 1, 4) || '-' ||
                            SUBSTR(datenaiss, 5, 2) || '-' ||
                            SUBSTR(datenaiss, 7, 2)
                        AS DATE)
                    ELSE NULL
                END as datenaiss,
                lieunaiss,
                commnaiss,
                paysnaiss,
                -- Parse death date (YYYYMMDD -> DATE)
                CASE
                    WHEN LENGTH(TRIM(datedeces)) >= 8 THEN
                        TRY_CAST(
                            SUBSTR(datedeces, 1, 4) || '-' ||
                            SUBSTR(datedeces, 5, 2) || '-' ||
                            SUBSTR(datedeces, 7, 2)
                        AS DATE)
                    ELSE NULL
                END as datedeces,
                lieudeces,
                actedeces,
                -- Extract year, month, day from death date
                TRY_CAST(SUBSTR(datedeces, 1, 4) AS INTEGER) as annee_deces,
                TRY_CAST(SUBSTR(datedeces, 5, 2) AS INTEGER) as mois_deces,
                TRY_CAST(SUBSTR(datedeces, 7, 2) AS INTEGER) as jour_deces,
                -- Calculate age at death
                CASE
                    WHEN LENGTH(TRIM(datenaiss)) >= 8 AND LENGTH(TRIM(datedeces)) >= 8 THEN
                        ROUND(
                            (TRY_CAST(SUBSTR(datedeces, 1, 4) AS INTEGER) -
                             TRY_CAST(SUBSTR(datenaiss, 1, 4) AS INTEGER)) +
                            (TRY_CAST(SUBSTR(datedeces, 5, 2) || SUBSTR(datedeces, 7, 2) AS INTEGER) -
                             TRY_CAST(SUBSTR(datenaiss, 5, 2) || SUBSTR(datenaiss, 7, 2) AS INTEGER)) / 10000.0
                        , 2)
                    ELSE NULL
                END as age_deces,
                -- Extract department (2 chars, or 3 for DOM-TOM 97xxx)
                CASE
                    WHEN SUBSTR(lieudeces, 1, 2) = '97' THEN SUBSTR(lieudeces, 1, 3)
                    WHEN SUBSTR(lieudeces, 1, 2) IN ('2A', '2B') THEN SUBSTR(lieudeces, 1, 2)
                    WHEN LENGTH(lieudeces) >= 2 THEN SUBSTR(lieudeces, 1, 2)
                    ELSE '00'
                END as departement,
                -- Create unique hash for deduplication
                MD5(COALESCE(nomprenom, '') || COALESCE(datenaiss, '') ||
                    COALESCE(datedeces, '') || COALESCE(lieudeces, '')) as hash_unique
            FROM temp_normalized
            WHERE LENGTH(TRIM(datedeces)) >= 8
        """)

        # Progress: Transformed, starting insert
        if progress_callback:
            try:
                progress_callback(0.6, total_rows)
            except TypeError:
                progress_callback(0.6)

        # Insert into main table with deduplication (INSERT OR IGNORE)
        conn.execute("""
            INSERT OR IGNORE INTO deces (
                nomprenom, sexe, datenaiss, lieunaiss, commnaiss, paysnaiss,
                datedeces, lieudeces, actedeces,
                annee_deces, mois_deces, jour_deces, age_deces, departement,
                hash_unique
            )
            SELECT
                nomprenom, sexe, datenaiss, lieunaiss, commnaiss, paysnaiss,
                datedeces, lieudeces, actedeces,
                annee_deces, mois_deces, jour_deces, age_deces, departement,
                hash_unique
            FROM temp_transformed
        """)

        # Progress: Insert done
        if progress_callback:
            try:
                progress_callback(0.9, total_rows)
            except TypeError:
                progress_callback(0.9)

        # Get count after import
        count_after = conn.execute("SELECT COUNT(*) FROM deces").fetchone()[0]
        rows_added = count_after - count_before
        duplicates = total_rows - rows_added

        # Clean up temp tables
        conn.execute("DROP TABLE IF EXISTS temp_import")
        conn.execute("DROP TABLE IF EXISTS temp_normalized")
        conn.execute("DROP TABLE IF EXISTS temp_transformed")

        # Log import
        conn.execute("""
            INSERT INTO import_logs (filename, rows_added, rows_duplicates, status)
            VALUES (?, ?, ?, ?)
        """, [filename, rows_added, duplicates, 'success'])

        conn.close()

        # Progress: Complete
        if progress_callback:
            try:
                progress_callback(1.0, total_rows)
            except TypeError:
                progress_callback(1.0)

        return rows_added, duplicates, f"Import réussi: {rows_added} lignes ajoutées, {duplicates} doublons ignorés"

    except Exception as e:
        return 0, 0, f"Erreur: {str(e)}"


# ============================================================================
# QUERY FUNCTIONS FOR DASHBOARD
# ============================================================================

def get_available_years() -> List[int]:
    """Get list of years with data."""
    with db_connection(read_only=True) as conn:
        result = conn.execute("""
            SELECT DISTINCT annee_deces
            FROM deces
            WHERE annee_deces IS NOT NULL
            ORDER BY annee_deces DESC
        """).fetchall()
        return [r[0] for r in result]


def get_available_departments() -> List[str]:
    """Get list of departments with data."""
    with db_connection(read_only=True) as conn:
        result = conn.execute("""
            SELECT DISTINCT departement
            FROM deces
            WHERE departement IS NOT NULL AND departement != '00'
            ORDER BY departement
        """).fetchall()
        return [r[0] for r in result]


def get_total_deaths(year: Optional[int] = None, month: Optional[int] = None,
                     department: Optional[str] = None, sexe: Optional[int] = None,
                     age_group: Optional[tuple] = None) -> int:
    """Get total death count with optional filters."""
    with db_connection(read_only=True) as conn:
        query = "SELECT COUNT(*) FROM deces WHERE 1=1"
        params = []

        if year:
            query += " AND annee_deces = ?"
            params.append(year)
        if month:
            query += " AND mois_deces = ?"
            params.append(month)
        if department:
            query += " AND departement = ?"
            params.append(department)
        if sexe:
            query += " AND sexe = ?"
            params.append(sexe)
        if age_group:
            age_min, age_max = age_group
            query += " AND age_deces >= ? AND age_deces <= ?"
            params.append(age_min)
            params.append(age_max)

        result = conn.execute(query, params).fetchone()[0]
        return result


def get_average_age(year: Optional[int] = None, month: Optional[int] = None,
                    department: Optional[str] = None, sexe: Optional[int] = None,
                    age_group: Optional[tuple] = None) -> Optional[float]:
    """Get average age at death with optional filters."""
    with db_connection(read_only=True) as conn:
        query = "SELECT AVG(age_deces) FROM deces WHERE age_deces IS NOT NULL"
        params = []

        if year:
            query += " AND annee_deces = ?"
            params.append(year)
        if month:
            query += " AND mois_deces = ?"
            params.append(month)
        if department:
            query += " AND departement = ?"
            params.append(department)
        if sexe:
            query += " AND sexe = ?"
            params.append(sexe)
        if age_group:
            age_min, age_max = age_group
            query += " AND age_deces >= ? AND age_deces <= ?"
            params.append(age_min)
            params.append(age_max)

        result = conn.execute(query, params).fetchone()[0]
        return round(result, 1) if result else None


def get_yoy_evolution(year: int, month: Optional[int] = None,
                      department: Optional[str] = None, sexe: Optional[int] = None) -> Optional[float]:
    """Calculate year-over-year evolution percentage."""
    current = get_total_deaths(year, month, department, sexe)
    previous = get_total_deaths(year - 1, month, department, sexe)

    if previous and previous > 0:
        return round(((current - previous) / previous) * 100, 1)
    return None


def get_daily_deaths(year: int, month: Optional[int] = None,
                     department: Optional[str] = None, sexe: Optional[int] = None) -> pd.DataFrame:
    """Get daily death counts for time series."""
    with db_connection(read_only=True) as conn:

        query = """
            SELECT datedeces, COUNT(*) as count
            FROM deces
            WHERE annee_deces = ?
        """
        params = [year]

        if month:
            query += " AND mois_deces = ?"
            params.append(month)
        if department:
            query += " AND departement = ?"
            params.append(department)
        if sexe:
            query += " AND sexe = ?"
            params.append(sexe)

        query += " GROUP BY datedeces ORDER BY datedeces"

        df = conn.execute(query, params).df()
        
    return df


def get_deaths_by_month_day(year: int, department: Optional[str] = None,
                            sexe: Optional[int] = None, age_group: Optional[tuple] = None) -> pd.DataFrame:
    """Get death counts grouped by month and day for heatmap."""
    with db_connection(read_only=True) as conn:

        query = """
            SELECT mois_deces as month, jour_deces as day, COUNT(*) as count
            FROM deces
            WHERE annee_deces = ?
        """
        params = [year]

        if department:
            query += " AND departement = ?"
            params.append(department)
        if sexe:
            query += " AND sexe = ?"
            params.append(sexe)
        if age_group:
            age_min, age_max = age_group
            query += " AND age_deces >= ? AND age_deces <= ?"
            params.append(age_min)
            params.append(age_max)

        query += " GROUP BY mois_deces, jour_deces ORDER BY mois_deces, jour_deces"

        df = conn.execute(query, params).df()

    return df


def get_age_pyramid_data(year: Optional[int] = None, month: Optional[int] = None,
                         department: Optional[str] = None, sexe: Optional[int] = None,
                         age_group: Optional[tuple] = None) -> pd.DataFrame:
    """Get age distribution by sex for pyramid chart."""
    with db_connection(read_only=True) as conn:

        query = """
            SELECT
                CAST(FLOOR(age_deces / 5) * 5 AS INTEGER) as age_group,
                sexe,
                COUNT(*) as count
            FROM deces
            WHERE age_deces IS NOT NULL AND sexe IN (1, 2)
        """
        params = []

        if year:
            query += " AND annee_deces = ?"
            params.append(year)
        if month:
            query += " AND mois_deces = ?"
            params.append(month)
        if department:
            query += " AND departement = ?"
            params.append(department)
        if sexe:
            query += " AND sexe = ?"
            params.append(sexe)
        if age_group:
            age_min, age_max = age_group
            query += " AND age_deces >= ? AND age_deces <= ?"
            params.append(age_min)
            params.append(age_max)

        query += " GROUP BY age_group, sexe ORDER BY age_group"

        df = conn.execute(query, params).df()

    return df


def get_deaths_by_year(month: Optional[int] = None, department: Optional[str] = None,
                       sexe: Optional[int] = None, age_group: Optional[tuple] = None) -> pd.DataFrame:
    """Get death counts by year for time series."""
    with db_connection(read_only=True) as conn:

        query = """
            SELECT annee_deces, COUNT(*) as count
            FROM deces
            WHERE annee_deces IS NOT NULL
        """
        params = []

        if month:
            query += " AND mois_deces = ?"
            params.append(month)
        if department:
            query += " AND departement = ?"
            params.append(department)
        if sexe:
            query += " AND sexe = ?"
            params.append(sexe)
        if age_group:
            age_min, age_max = age_group
            query += " AND age_deces >= ? AND age_deces <= ?"
            params.append(age_min)
            params.append(age_max)

        query += " GROUP BY annee_deces ORDER BY annee_deces"

        df = conn.execute(query, params).df()
        
    return df


def get_deaths_by_department(year: Optional[int] = None, month: Optional[int] = None,
                             sexe: Optional[int] = None, age_group: Optional[tuple] = None) -> pd.DataFrame:
    """Get death counts by department for map."""
    with db_connection(read_only=True) as conn:

        query = """
            SELECT departement as code, COUNT(*) as count
            FROM deces
            WHERE departement IS NOT NULL AND departement != '00'
        """
        params = []

        if year:
            query += " AND annee_deces = ?"
            params.append(year)
        if month:
            query += " AND mois_deces = ?"
            params.append(month)
        if sexe:
            query += " AND sexe = ?"
            params.append(sexe)
        if age_group:
            age_min, age_max = age_group
            query += " AND age_deces >= ? AND age_deces <= ?"
            params.append(age_min)
            params.append(age_max)

        query += " GROUP BY departement ORDER BY departement"

        df = conn.execute(query, params).df()

    return df


def get_database_stats() -> dict:
    """Get database statistics."""
    with db_connection(read_only=True) as conn:

        stats = {
            'total_records': conn.execute("SELECT COUNT(*) FROM deces").fetchone()[0],
            'date_range': conn.execute("""
                SELECT MIN(datedeces), MAX(datedeces) FROM deces
            """).fetchone(),
            'departments_count': conn.execute("""
                SELECT COUNT(DISTINCT departement) FROM deces WHERE departement != '00'
            """).fetchone()[0],
            'imports_count': conn.execute("SELECT COUNT(*) FROM import_logs").fetchone()[0]
        }

        
    return stats


def get_import_history() -> pd.DataFrame:
    """Get import history log."""
    with db_connection(read_only=True) as conn:
        df = conn.execute("""
            SELECT filename, import_date, rows_added, rows_duplicates, status
            FROM import_logs
            ORDER BY import_date DESC
            LIMIT 50
        """).df()
        
    return df


# ============================================================================
# GEOJSON MANAGEMENT
# ============================================================================

def download_geojson() -> bool:
    """Download French departments GeoJSON if not exists."""
    if GEOJSON_PATH.exists():
        return True

    try:
        response = requests.get(GEOJSON_URL, timeout=30)
        response.raise_for_status()

        with open(GEOJSON_PATH, 'w', encoding='utf-8') as f:
            f.write(response.text)

        return True
    except Exception as e:
        print(f"Erreur téléchargement GeoJSON: {e}")
        return False


def get_geojson() -> Optional[dict]:
    """Load GeoJSON for French departments."""
    import json

    if not GEOJSON_PATH.exists():
        if not download_geojson():
            return None

    try:
        with open(GEOJSON_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return None


# ============================================================================
# POPULATION DATA MANAGEMENT
# ============================================================================

# Cache pour les données de population
_population_cache = {
    'dept': None,
    'age': None,
    'complete': None
}


def load_population_dept() -> pd.DataFrame:
    """Load population data by department and year."""
    if _population_cache['dept'] is not None:
        return _population_cache['dept']

    if not POPULATION_DEPT_PATH.exists():
        return pd.DataFrame(columns=['annee', 'departement', 'population'])

    try:
        df = pd.read_csv(POPULATION_DEPT_PATH)
        _population_cache['dept'] = df
        return df
    except Exception:
        return pd.DataFrame(columns=['annee', 'departement', 'population'])


def load_population_age() -> pd.DataFrame:
    """Load population data by age and year."""
    if _population_cache['age'] is not None:
        return _population_cache['age']

    if not POPULATION_AGE_PATH.exists():
        return pd.DataFrame(columns=['annee', 'age_min', 'age_max', 'population'])

    try:
        df = pd.read_csv(POPULATION_AGE_PATH)
        _population_cache['age'] = df
        return df
    except Exception:
        return pd.DataFrame(columns=['annee', 'age_min', 'age_max', 'population'])


def load_population_complete() -> pd.DataFrame:
    """Load complete population data (dept x age x year)."""
    if _population_cache['complete'] is not None:
        return _population_cache['complete']

    if not POPULATION_COMPLETE_PATH.exists():
        return pd.DataFrame(columns=['annee', 'departement', 'age_min', 'age_max', 'population'])

    try:
        df = pd.read_csv(POPULATION_COMPLETE_PATH)
        _population_cache['complete'] = df
        return df
    except Exception:
        return pd.DataFrame(columns=['annee', 'departement', 'age_min', 'age_max', 'population'])


def get_population_dept(year: int, dept: str) -> Optional[int]:
    """Get population for a specific department and year."""
    df = load_population_dept()

    if df.empty:
        return None

    result = df[(df['annee'] == year) & (df['departement'] == dept)]

    if not result.empty:
        return int(result.iloc[0]['population'])

    return None


def get_population_age(year: int, age_min: int, age_max: int) -> Optional[int]:
    """Get population for a specific age range and year."""
    df = load_population_age()

    if df.empty:
        return None

    result = df[(df['annee'] == year) & (df['age_min'] == age_min) & (df['age_max'] == age_max)]

    if not result.empty:
        return int(result.iloc[0]['population'])

    return None


def get_total_population_year(year: int) -> Optional[int]:
    """Get total population for a year (sum of all departments)."""
    df = load_population_dept()

    if df.empty:
        return None

    result = df[df['annee'] == year]['population'].sum()
    return int(result) if result > 0 else None


# ============================================================================
# MORTALITY RATE CALCULATIONS
# ============================================================================

def calculate_mortality_rate(deaths: int, population: int, per: int = 100000) -> Optional[float]:
    """
    Calculate mortality rate per X inhabitants.

    Args:
        deaths: Number of deaths
        population: Population size
        per: Rate per X inhabitants (default: 100,000)

    Returns:
        Mortality rate or None if population is 0
    """
    if population == 0:
        return None

    return round((deaths / population) * per, 2)


def get_deaths_by_department_with_rates(year: Optional[int] = None, month: Optional[int] = None,
                                         sexe: Optional[int] = None, age_group: Optional[tuple] = None) -> pd.DataFrame:
    """Get death counts by department with population and mortality rates."""
    df_deaths = get_deaths_by_department(year, month, sexe, age_group)

    if df_deaths.empty or not year:
        return df_deaths

    # Add population data
    df_pop = load_population_dept()

    if df_pop.empty:
        df_deaths['population'] = None
        df_deaths['rate'] = None
        return df_deaths

    # Merge with population
    df_pop_year = df_pop[df_pop['annee'] == year][['departement', 'population']]
    df_result = df_deaths.merge(df_pop_year, left_on='code', right_on='departement', how='left')
    df_result = df_result.drop('departement', axis=1)

    # Calculate mortality rate per 100,000
    df_result['rate'] = df_result.apply(
        lambda row: calculate_mortality_rate(row['count'], row['population']) if pd.notna(row['population']) else None,
        axis=1
    )

    return df_result


# ============================================================================
# AGE TRENDS ANALYSIS
# ============================================================================

def get_mortality_by_age_year(age_group_size: int = 5, year_filter: Optional[List[int]] = None,
                               month: Optional[int] = None, dept: Optional[str] = None,
                               sexe: Optional[int] = None, age_group: Optional[tuple] = None) -> pd.DataFrame:
    """
    Get mortality data grouped by age and year for heatmap and trends.

    Args:
        age_group_size: Size of age groups (5 or 10 years)
        year_filter: List of years to include (None = all)
        month: Filter by month
        dept: Filter by department
        sexe: Filter by sex
        age_group: Filter by age range (age_min, age_max)

    Returns:
        DataFrame with columns: age_group, annee, deaths, population, rate
    """
    with db_connection(read_only=True) as conn:

        query = f"""
            SELECT
                CAST(FLOOR(age_deces / {age_group_size}) * {age_group_size} AS INTEGER) as age_group,
                annee_deces,
                COUNT(*) as deaths
            FROM deces
            WHERE age_deces IS NOT NULL
        """
        params = []

        if year_filter:
            placeholders = ','.join(['?'] * len(year_filter))
            query += f" AND annee_deces IN ({placeholders})"
            params.extend(year_filter)

        if month:
            query += " AND mois_deces = ?"
            params.append(month)

        if dept:
            query += " AND departement = ?"
            params.append(dept)

        if sexe:
            query += " AND sexe = ?"
            params.append(sexe)

        if age_group:
            age_min, age_max = age_group
            query += " AND age_deces >= ? AND age_deces <= ?"
            params.append(age_min)
            params.append(age_max)

        query += " GROUP BY age_group, annee_deces ORDER BY age_group, annee_deces"

        df = conn.execute(query, params).df()
        

    if df.empty:
        return df

    # Add population data
    df_pop = load_population_age()

    if not df_pop.empty:
        # Merge population data
        df_result = []

        for _, row in df.iterrows():
            age_min = int(row['age_group'])
            age_max = age_min + age_group_size - 1
            year = int(row['annee_deces'])
            deaths = int(row['deaths'])

            # Get population for this age group and year
            pop_data = df_pop[
                (df_pop['annee'] == year) &
                (df_pop['age_min'] == age_min)
            ]

            population = int(pop_data.iloc[0]['population']) if not pop_data.empty else None
            rate = calculate_mortality_rate(deaths, population) if population else None

            df_result.append({
                'age_group': age_min,
                'age_max': age_max,
                'annee': year,
                'deaths': deaths,
                'population': population,
                'rate': rate
            })

        return pd.DataFrame(df_result)

    # No population data available
    df['population'] = None
    df['rate'] = None
    df.rename(columns={'annee_deces': 'annee'}, inplace=True)
    df['age_max'] = df['age_group'] + age_group_size - 1

    return df


def get_age_trends_summary(years: List[int], age_group_size: int = 5) -> pd.DataFrame:
    """
    Get summary statistics for age trends across multiple years.

    Returns:
        DataFrame with evolution percentages and other stats
    """
    df = get_mortality_by_age_year(age_group_size=age_group_size, year_filter=years)

    if df.empty:
        return df

    # Pivot to get years as columns
    pivot = df.pivot(index='age_group', columns='annee', values='deaths').fillna(0)

    # Calculate evolution % for each consecutive year
    result = []

    for age in pivot.index:
        row_data = {'age_group': int(age)}

        for year in sorted(years):
            if year in pivot.columns:
                row_data[f'deaths_{year}'] = int(pivot.loc[age, year])

        # Calculate YoY evolution for the last year
        if len(years) >= 2:
            sorted_years = sorted(years)
            last_year = sorted_years[-1]
            prev_year = sorted_years[-2]

            if last_year in pivot.columns and prev_year in pivot.columns:
                current = pivot.loc[age, last_year]
                previous = pivot.loc[age, prev_year]

                if previous > 0:
                    evolution = ((current - previous) / previous) * 100
                    row_data['evolution_pct'] = round(evolution, 1)
                else:
                    row_data['evolution_pct'] = None

        result.append(row_data)

    return pd.DataFrame(result)


def get_median_age_by_year(years: Optional[List[int]] = None, month: Optional[int] = None,
                           dept: Optional[str] = None, sexe: Optional[int] = None,
                           age_group: Optional[tuple] = None) -> pd.DataFrame:
    """Get median age of death by year."""
    with db_connection(read_only=True) as conn:

        query = """
            SELECT
                annee_deces as annee,
                PERCENTILE_CONT(0.5) WITHIN GROUP (ORDER BY age_deces) as median_age,
                COUNT(*) as total_deaths
            FROM deces
            WHERE age_deces IS NOT NULL
        """
        params = []

        if years:
            placeholders = ','.join(['?'] * len(years))
            query += f" AND annee_deces IN ({placeholders})"
            params.extend(years)

        if month:
            query += " AND mois_deces = ?"
            params.append(month)

        if dept:
            query += " AND departement = ?"
            params.append(dept)

        if sexe:
            query += " AND sexe = ?"
            params.append(sexe)

        if age_group:
            age_min, age_max = age_group
            query += " AND age_deces >= ? AND age_deces <= ?"
            params.append(age_min)
            params.append(age_max)

        query += " GROUP BY annee_deces ORDER BY annee_deces"

        df = conn.execute(query, params).df()


    return df


def get_most_affected_age_group(year: int, age_group_size: int = 5, month: Optional[int] = None,
                                dept: Optional[str] = None, sexe: Optional[int] = None,
                                age_group: Optional[tuple] = None) -> Tuple[Optional[int], Optional[int]]:
    """
    Get the most affected age group for a specific year.

    Returns:
        Tuple of (age_group, death_count)
    """
    df = get_mortality_by_age_year(
        age_group_size=age_group_size,
        year_filter=[year],
        month=month,
        dept=dept,
        sexe=sexe,
        age_group=age_group
    )

    if df.empty:
        return None, None

    max_row = df.loc[df['deaths'].idxmax()]
    return int(max_row['age_group']), int(max_row['deaths'])


# ============================================================================
# EXCEL EXPORT
# ============================================================================

def export_age_trends_to_excel(years: List[int], age_group_size: int = 5,
                                month: Optional[int] = None, dept: Optional[str] = None,
                                sexe: Optional[int] = None, age_group: Optional[tuple] = None) -> bytes:
    """
    Export age trends data to Excel format with filters enabled.

    Args:
        years: List of years to include
        age_group_size: Size of age groups
        month: Filter by month
        dept: Filter by department
        sexe: Filter by sex
        age_group: Filter by age range (age_min, age_max)

    Returns:
        Bytes of Excel file
    """
    import io

    # Get data
    df = get_mortality_by_age_year(
        age_group_size=age_group_size,
        year_filter=years,
        month=month,
        dept=dept,
        sexe=sexe,
        age_group=age_group
    )

    if df.empty:
        # Return empty workbook
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame().to_excel(writer, index=False, sheet_name='Données')
        output.seek(0)
        return output.getvalue()

    # Pivot data for better Excel format
    pivot_deaths = df.pivot(index='age_group', columns='annee', values='deaths').fillna(0)
    pivot_rates = df.pivot(index='age_group', columns='annee', values='rate').fillna(0)

    # Reset index to include age_group as column
    pivot_deaths = pivot_deaths.reset_index()
    pivot_rates = pivot_rates.reset_index()

    # Rename columns
    pivot_deaths.columns = ['Tranche d\'âge'] + [f'Décès {int(year)}' for year in pivot_deaths.columns[1:]]
    pivot_rates.columns = ['Tranche d\'âge'] + [f'Taux {int(year)}' for year in pivot_rates.columns[1:]]

    # Create age labels
    pivot_deaths['Tranche d\'âge'] = pivot_deaths['Tranche d\'âge'].apply(
        lambda x: f"{int(x)}-{int(x) + age_group_size - 1} ans"
    )
    pivot_rates['Tranche d\'âge'] = pivot_rates['Tranche d\'âge'].apply(
        lambda x: f"{int(x)}-{int(x) + age_group_size - 1} ans"
    )

    # Create Excel file
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        # Sheet 1: Nombre de décès
        pivot_deaths.to_excel(writer, index=False, sheet_name='Décès par âge')

        # Sheet 2: Taux de mortalité
        pivot_rates.to_excel(writer, index=False, sheet_name='Taux par âge')

        # Sheet 3: Données brutes
        df_export = df.copy()
        df_export['age_label'] = df_export['age_group'].apply(
            lambda x: f"{int(x)}-{int(x) + age_group_size - 1} ans"
        )
        df_export = df_export[['age_label', 'annee', 'deaths', 'population', 'rate']]
        df_export.columns = ['Tranche d\'âge', 'Année', 'Décès', 'Population', 'Taux (/100k)']
        df_export.to_excel(writer, index=False, sheet_name='Données brutes')

        # Enable autofilter on all sheets
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            worksheet.auto_filter.ref = worksheet.dimensions

    output.seek(0)
    return output.getvalue()


# Initialize database on module import
init_database()
