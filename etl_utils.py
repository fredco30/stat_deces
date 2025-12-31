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


# Database configuration
DB_PATH = Path(__file__).parent / "mortality_data.duckdb"
GEOJSON_URL = "https://raw.githubusercontent.com/gregoiredavid/france-geojson/master/departements.geojson"
GEOJSON_PATH = Path(__file__).parent / "departements.geojson"


def get_connection() -> duckdb.DuckDBPyConnection:
    """Get a DuckDB connection."""
    return duckdb.connect(str(DB_PATH))


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
    conn = get_connection()
    result = conn.execute("""
        SELECT DISTINCT annee_deces
        FROM deces
        WHERE annee_deces IS NOT NULL
        ORDER BY annee_deces DESC
    """).fetchall()
    conn.close()
    return [r[0] for r in result]


def get_available_departments() -> List[str]:
    """Get list of departments with data."""
    conn = get_connection()
    result = conn.execute("""
        SELECT DISTINCT departement
        FROM deces
        WHERE departement IS NOT NULL AND departement != '00'
        ORDER BY departement
    """).fetchall()
    conn.close()
    return [r[0] for r in result]


def get_total_deaths(year: Optional[int] = None, month: Optional[int] = None,
                     department: Optional[str] = None, sexe: Optional[int] = None) -> int:
    """Get total death count with optional filters."""
    conn = get_connection()

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

    result = conn.execute(query, params).fetchone()[0]
    conn.close()
    return result


def get_deaths_by_year(month: Optional[int] = None,
                       department: Optional[str] = None,
                       sexe: Optional[int] = None,
                       min_threshold: int = 1000) -> pd.DataFrame:
    """
    Get death counts grouped by year with optional filters.
    Returns only years that have significant data (above threshold).

    Args:
        month: Filter by month
        department: Filter by department
        sexe: Filter by sex
        min_threshold: Minimum deaths per year to include (default 1000)

    Returns:
        DataFrame with columns: annee_deces, count
    """
    conn = get_connection()

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

    query += f" GROUP BY annee_deces HAVING COUNT(*) >= {min_threshold} ORDER BY annee_deces"

    df = conn.execute(query, params).df()
    conn.close()
    return df


def get_average_age(year: Optional[int] = None, month: Optional[int] = None,
                    department: Optional[str] = None, sexe: Optional[int] = None) -> Optional[float]:
    """Get average age at death with optional filters."""
    conn = get_connection()

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

    result = conn.execute(query, params).fetchone()[0]
    conn.close()
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
    conn = get_connection()

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
    conn.close()
    return df


def get_deaths_by_month_day(year: int, department: Optional[str] = None,
                            sexe: Optional[int] = None) -> pd.DataFrame:
    """Get death counts grouped by month and day for heatmap."""
    conn = get_connection()

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

    query += " GROUP BY mois_deces, jour_deces ORDER BY mois_deces, jour_deces"

    df = conn.execute(query, params).df()
    conn.close()
    return df


def get_age_pyramid_data(year: Optional[int] = None, month: Optional[int] = None,
                         department: Optional[str] = None) -> pd.DataFrame:
    """Get age distribution by sex for pyramid chart."""
    conn = get_connection()

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

    query += " GROUP BY age_group, sexe ORDER BY age_group"

    df = conn.execute(query, params).df()
    conn.close()
    return df


def get_deaths_by_department(year: Optional[int] = None, month: Optional[int] = None,
                             sexe: Optional[int] = None) -> pd.DataFrame:
    """Get death counts by department for map."""
    conn = get_connection()

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

    query += " GROUP BY departement ORDER BY departement"

    df = conn.execute(query, params).df()
    conn.close()
    return df


def get_database_stats() -> dict:
    """Get database statistics."""
    conn = get_connection()

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

    conn.close()
    return stats


def get_import_history() -> pd.DataFrame:
    """Get import history log."""
    conn = get_connection()
    df = conn.execute("""
        SELECT filename, import_date, rows_added, rows_duplicates, status
        FROM import_logs
        ORDER BY import_date DESC
        LIMIT 50
    """).df()
    conn.close()
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


# Initialize database on module import
init_database()
