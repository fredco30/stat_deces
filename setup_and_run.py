#!/usr/bin/env python3
"""
Lanceur Automatique - Application Mortalité France
Installe automatiquement toutes les dépendances et lance l'application.
Compatible Windows, Linux, macOS.
"""

import subprocess
import sys
import os
import platform
from pathlib import Path


# ============================================================================
# CONFIGURATION
# ============================================================================

APP_NAME = "Mortalité France - Tableau de Bord"
REQUIREMENTS_FILE = "requirements.txt"
MAIN_APP = "launcher.py"
VENV_NAME = "venv"

# Couleurs pour le terminal (désactivées sur Windows CMD par défaut)
class Colors:
    if platform.system() == "Windows":
        # Activer les couleurs ANSI sur Windows 10+
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
            HEADER = '\033[95m'
            OKBLUE = '\033[94m'
            OKCYAN = '\033[96m'
            OKGREEN = '\033[92m'
            WARNING = '\033[93m'
            FAIL = '\033[91m'
            ENDC = '\033[0m'
            BOLD = '\033[1m'
        except Exception:
            HEADER = OKBLUE = OKCYAN = OKGREEN = WARNING = FAIL = ENDC = BOLD = ''
    else:
        HEADER = '\033[95m'
        OKBLUE = '\033[94m'
        OKCYAN = '\033[96m'
        OKGREEN = '\033[92m'
        WARNING = '\033[93m'
        FAIL = '\033[91m'
        ENDC = '\033[0m'
        BOLD = '\033[1m'


def print_banner():
    """Affiche la bannière de l'application."""
    banner = f"""
{Colors.OKCYAN}
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║      📊  INSTALLATION & LANCEMENT AUTOMATIQUE  📊                ║
    ║                                                                   ║
    ║           {APP_NAME}                        ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
{Colors.ENDC}
    """
    print(banner)


def print_step(step_num: int, total: int, message: str):
    """Affiche une étape du processus."""
    print(f"\n{Colors.OKBLUE}[{step_num}/{total}]{Colors.ENDC} {Colors.BOLD}{message}{Colors.ENDC}")
    print("-" * 60)


def print_success(message: str):
    """Affiche un message de succès."""
    print(f"{Colors.OKGREEN}✓ {message}{Colors.ENDC}")


def print_warning(message: str):
    """Affiche un avertissement."""
    print(f"{Colors.WARNING}⚠ {message}{Colors.ENDC}")


def print_error(message: str):
    """Affiche une erreur."""
    print(f"{Colors.FAIL}✗ {message}{Colors.ENDC}")


def get_script_directory() -> Path:
    """Retourne le répertoire du script."""
    return Path(__file__).parent.resolve()


def check_python_version() -> bool:
    """Vérifie la version de Python."""
    version = sys.version_info
    print(f"   Python détecté: {version.major}.{version.minor}.{version.micro}")
    print(f"   Chemin: {sys.executable}")

    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print_error("Python 3.9+ est requis!")
        return False

    print_success("Version Python compatible")
    return True


def check_pip() -> bool:
    """Vérifie que pip est disponible."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "--version"],
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            pip_version = result.stdout.strip().split()[1]
            print(f"   pip version: {pip_version}")
            print_success("pip est disponible")
            return True
    except Exception as e:
        pass

    print_error("pip n'est pas disponible")
    return False


def upgrade_pip():
    """Met à jour pip vers la dernière version."""
    print("   Mise à jour de pip...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "--upgrade", "pip"],
            capture_output=True,
            check=True
        )
        print_success("pip mis à jour")
    except subprocess.CalledProcessError:
        print_warning("Impossible de mettre à jour pip (non critique)")


def create_virtual_env(venv_path: Path) -> bool:
    """Crée un environnement virtuel."""
    if venv_path.exists():
        print(f"   Environnement virtuel existant trouvé: {venv_path}")
        print_success("Utilisation de l'environnement existant")
        return True

    print(f"   Création de l'environnement virtuel: {venv_path}")
    try:
        subprocess.run(
            [sys.executable, "-m", "venv", str(venv_path)],
            check=True
        )
        print_success("Environnement virtuel créé")
        return True
    except subprocess.CalledProcessError as e:
        print_error(f"Erreur lors de la création du venv: {e}")
        return False


def get_venv_python(venv_path: Path) -> Path:
    """Retourne le chemin vers Python dans le venv."""
    if platform.system() == "Windows":
        return venv_path / "Scripts" / "python.exe"
    else:
        return venv_path / "bin" / "python"


def install_requirements(python_path: Path, requirements_path: Path) -> bool:
    """Installe les dépendances depuis requirements.txt."""
    if not requirements_path.exists():
        print_error(f"Fichier {requirements_path} non trouvé!")
        return False

    print(f"   Fichier: {requirements_path}")

    # Lire et afficher les packages
    with open(requirements_path, 'r') as f:
        packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]

    print(f"   Packages à installer: {len(packages)}")
    for pkg in packages:
        print(f"      • {pkg}")

    print("\n   Installation en cours...")

    try:
        result = subprocess.run(
            [str(python_path), "-m", "pip", "install", "-r", str(requirements_path)],
            capture_output=True,
            text=True
        )

        if result.returncode == 0:
            print_success("Toutes les dépendances ont été installées")
            return True
        else:
            print_error("Erreur lors de l'installation")
            print(f"   {result.stderr}")
            return False

    except subprocess.CalledProcessError as e:
        print_error(f"Erreur: {e}")
        return False


def install_optional_packages(python_path: Path):
    """Installe les packages optionnels pour une meilleure expérience."""
    optional_packages = [
        ("watchdog", "Rechargement automatique"),
        ("pyarrow", "Performance améliorée pour les DataFrames"),
    ]

    print("   Packages optionnels:")

    for package, description in optional_packages:
        print(f"      • {package}: {description}")
        try:
            result = subprocess.run(
                [str(python_path), "-m", "pip", "install", package],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print(f"        {Colors.OKGREEN}✓ Installé{Colors.ENDC}")
            else:
                print(f"        {Colors.WARNING}⚠ Ignoré (non critique){Colors.ENDC}")
        except Exception:
            print(f"        {Colors.WARNING}⚠ Ignoré (non critique){Colors.ENDC}")


def verify_installation(python_path: Path) -> bool:
    """Vérifie que les packages critiques sont installés."""
    critical_packages = ['streamlit', 'duckdb', 'pandas', 'plotly', 'folium']

    print("   Vérification des packages critiques:")
    all_ok = True

    for package in critical_packages:
        try:
            result = subprocess.run(
                [str(python_path), "-c", f"import {package}; print({package}.__version__)"],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                version = result.stdout.strip()
                print(f"      {Colors.OKGREEN}✓{Colors.ENDC} {package}: {version}")
            else:
                print(f"      {Colors.FAIL}✗{Colors.ENDC} {package}: NON INSTALLÉ")
                all_ok = False
        except Exception:
            print(f"      {Colors.FAIL}✗{Colors.ENDC} {package}: ERREUR")
            all_ok = False

    if all_ok:
        print_success("Tous les packages critiques sont installés")
    else:
        print_error("Certains packages critiques sont manquants")

    return all_ok


def launch_application(python_path: Path, app_path: Path):
    """Lance l'application."""
    print(f"\n   Lancement de: {app_path}")
    print(f"   Avec Python: {python_path}")
    print("\n" + "=" * 60)
    print(f"{Colors.OKGREEN}   🚀 DÉMARRAGE DE L'APPLICATION...{Colors.ENDC}")
    print("=" * 60 + "\n")

    try:
        # Lancer l'application en mode interactif
        subprocess.run(
            [str(python_path), str(app_path)],
            cwd=str(app_path.parent)
        )
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Application arrêtée par l'utilisateur.{Colors.ENDC}")
    except Exception as e:
        print_error(f"Erreur lors du lancement: {e}")


def ask_user(question: str, default: bool = True) -> bool:
    """Pose une question oui/non à l'utilisateur."""
    default_str = "O/n" if default else "o/N"
    try:
        response = input(f"{question} [{default_str}]: ").strip().lower()
        if not response:
            return default
        return response in ['o', 'oui', 'y', 'yes']
    except EOFError:
        return default


def main():
    """Point d'entrée principal."""
    print_banner()

    script_dir = get_script_directory()
    os.chdir(script_dir)

    total_steps = 6

    # ========================================================================
    # ÉTAPE 1: Vérification de Python
    # ========================================================================
    print_step(1, total_steps, "Vérification de Python")
    if not check_python_version():
        print("\n❌ Installation impossible. Veuillez installer Python 3.9+")
        print("   Téléchargement: https://www.python.org/downloads/")
        input("\nAppuyez sur Entrée pour quitter...")
        sys.exit(1)

    # ========================================================================
    # ÉTAPE 2: Vérification de pip
    # ========================================================================
    print_step(2, total_steps, "Vérification de pip")
    if not check_pip():
        print("\n❌ pip n'est pas disponible. Installation requise.")
        input("\nAppuyez sur Entrée pour quitter...")
        sys.exit(1)

    # ========================================================================
    # ÉTAPE 3: Environnement virtuel (optionnel)
    # ========================================================================
    print_step(3, total_steps, "Configuration de l'environnement")

    venv_path = script_dir / VENV_NAME
    use_venv = False
    python_to_use = Path(sys.executable)

    # Vérifier si on est déjà dans un venv
    in_venv = hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix)

    if in_venv:
        print("   Environnement virtuel déjà actif")
        print_success("Utilisation de l'environnement actuel")
    else:
        print("   Voulez-vous créer/utiliser un environnement virtuel?")
        print("   (Recommandé pour isoler les dépendances)")

        if ask_user("   Créer un environnement virtuel?", default=True):
            if create_virtual_env(venv_path):
                python_to_use = get_venv_python(venv_path)
                use_venv = True
                print(f"   Python venv: {python_to_use}")
            else:
                print_warning("Utilisation de Python système à la place")
        else:
            print_warning("Installation dans Python système")

    # ========================================================================
    # ÉTAPE 4: Installation des dépendances
    # ========================================================================
    print_step(4, total_steps, "Installation des dépendances")

    # Mettre à jour pip
    upgrade_pip()

    # Installer requirements.txt
    requirements_path = script_dir / REQUIREMENTS_FILE
    if not install_requirements(python_to_use, requirements_path):
        print_error("L'installation des dépendances a échoué")
        if ask_user("Voulez-vous réessayer?", default=True):
            if not install_requirements(python_to_use, requirements_path):
                input("\nAppuyez sur Entrée pour quitter...")
                sys.exit(1)
        else:
            input("\nAppuyez sur Entrée pour quitter...")
            sys.exit(1)

    # ========================================================================
    # ÉTAPE 5: Packages optionnels
    # ========================================================================
    print_step(5, total_steps, "Installation des packages optionnels")
    install_optional_packages(python_to_use)

    # ========================================================================
    # ÉTAPE 6: Vérification finale
    # ========================================================================
    print_step(6, total_steps, "Vérification de l'installation")
    if not verify_installation(python_to_use):
        print_warning("Certains packages pourraient manquer, mais l'application peut fonctionner")

    # ========================================================================
    # LANCEMENT
    # ========================================================================
    print(f"\n{Colors.OKGREEN}{'='*60}{Colors.ENDC}")
    print(f"{Colors.OKGREEN}   ✓ INSTALLATION TERMINÉE AVEC SUCCÈS!{Colors.ENDC}")
    print(f"{Colors.OKGREEN}{'='*60}{Colors.ENDC}")

    if ask_user("\nVoulez-vous lancer l'application maintenant?", default=True):
        app_path = script_dir / MAIN_APP
        if app_path.exists():
            launch_application(python_to_use, app_path)
        else:
            print_error(f"Fichier {MAIN_APP} non trouvé!")
            print("   Vous pouvez lancer manuellement avec:")
            print(f"   {python_to_use} launcher.py")
    else:
        print("\n   Pour lancer l'application plus tard:")
        if use_venv:
            if platform.system() == "Windows":
                print(f"   1. Activez le venv: {venv_path}\\Scripts\\activate")
            else:
                print(f"   1. Activez le venv: source {venv_path}/bin/activate")
            print(f"   2. Lancez: python launcher.py")
        else:
            print(f"   python launcher.py")

    print("\n👋 Au revoir!")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠ Installation annulée par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        input("\nAppuyez sur Entrée pour quitter...")
        sys.exit(1)
