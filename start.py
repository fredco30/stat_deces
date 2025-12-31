#!/usr/bin/env python3
"""
Script de démarrage simplifié pour l'application Mortalité France
Détecte automatiquement la configuration et lance l'application.

Usage:
    python start.py              # Lance avec configuration automatique
    python start.py --port 8080  # Lance sur un port personnalisé
    python start.py --setup-only # Configure uniquement sans lancer
"""

import subprocess
import sys
from pathlib import Path
import argparse


def check_python_version():
    """Vérifie que Python 3.7+ est installé."""
    if sys.version_info < (3, 7):
        print("❌ Python 3.7 ou supérieur est requis")
        print(f"   Version actuelle : {sys.version}")
        sys.exit(1)


def check_dependencies():
    """Vérifie les dépendances critiques."""
    required = ['streamlit', 'duckdb', 'pandas', 'plotly']
    missing = []

    for package in required:
        try:
            __import__(package)
        except ImportError:
            missing.append(package)

    if missing:
        print("⚠️  Packages manquants détectés :\n")
        print(f"   {', '.join(missing)}\n")
        print("📦 Installation automatique...\n")

        try:
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
                check=True
            )
            print("\n✅ Dépendances installées avec succès !\n")
        except subprocess.CalledProcessError:
            print("\n❌ Erreur lors de l'installation des dépendances")
            print("   Installez-les manuellement avec :")
            print("   pip install -r requirements.txt\n")
            sys.exit(1)


def run_network_setup():
    """Exécute la configuration réseau si nécessaire."""
    config_file = Path(__file__).parent / ".streamlit" / "config.toml"

    if not config_file.exists():
        print("🔧 Première exécution détectée - Configuration du réseau...\n")
        setup_script = Path(__file__).parent / "setup_network.py"

        if setup_script.exists():
            subprocess.run([sys.executable, str(setup_script)])
        else:
            print("⚠️  Script de configuration manquant. Utilisation des paramètres par défaut.")

    else:
        print("✅ Configuration réseau existante détectée\n")


def launch_app(port=None):
    """Lance l'application Streamlit."""
    launcher = Path(__file__).parent / "launcher.py"

    if not launcher.exists():
        print(f"❌ Fichier launcher.py non trouvé : {launcher}")
        sys.exit(1)

    cmd = [sys.executable, str(launcher)]

    if port:
        cmd.extend(['--port', str(port)])

    print("🚀 Lancement de l'application Mortalité France...\n")

    try:
        subprocess.run(cmd)
    except KeyboardInterrupt:
        print("\n\n🛑 Application arrêtée par l'utilisateur")
        print("👋 À bientôt !\n")
    except Exception as e:
        print(f"\n❌ Erreur lors du lancement : {e}\n")
        sys.exit(1)


def print_banner():
    """Affiche la bannière."""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║         📊  MORTALITÉ FRANCE - DÉMARRAGE RAPIDE  📊              ║
║                                                                   ║
║         Application d'analyse des données de décès INSEE         ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def parse_arguments():
    """Parse les arguments de ligne de commande."""
    parser = argparse.ArgumentParser(
        description="Démarrage simplifié de l'application Mortalité France"
    )

    parser.add_argument(
        '-p', '--port',
        type=int,
        default=None,
        help="Port personnalisé (défaut: 8501)"
    )

    parser.add_argument(
        '--setup-only',
        action='store_true',
        help="Configure uniquement sans lancer l'application"
    )

    parser.add_argument(
        '--reconfigure',
        action='store_true',
        help="Force la reconfiguration réseau"
    )

    return parser.parse_args()


def main():
    """Point d'entrée principal."""
    args = parse_arguments()

    print_banner()

    # Vérifier Python
    check_python_version()

    # Vérifier les dépendances
    print("🔍 Vérification des dépendances...\n")
    check_dependencies()

    # Configuration réseau
    if args.reconfigure:
        print("🔧 Reconfiguration réseau forcée...\n")
        setup_script = Path(__file__).parent / "setup_network.py"
        if setup_script.exists():
            subprocess.run([sys.executable, str(setup_script)])
    else:
        run_network_setup()

    # Si setup-only, arrêter ici
    if args.setup_only:
        print("✅ Configuration terminée. Utilisez 'python start.py' pour lancer l'application.\n")
        return

    # Lancer l'application
    launch_app(args.port)


if __name__ == "__main__":
    main()
