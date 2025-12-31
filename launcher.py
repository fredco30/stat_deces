#!/usr/bin/env python3
"""
Intelligent Launcher for French Mortality Data Application
Detects IPs, displays access URLs, and launches Streamlit server.

Usage:
    python launcher.py              # Lance sur le port par défaut (8501)
    python launcher.py --port 8080  # Lance sur le port 8080
    python launcher.py -p 9000      # Lance sur le port 9000
"""

import subprocess
import socket
import sys
import os
import time
import webbrowser
import argparse
from pathlib import Path

# Configuration
DEFAULT_PORT = 8501  # Port par défaut Streamlit (évite conflit avec 5173/5174)
EXCLUDED_PORTS = [5173, 5174, 3000, 3001]  # Ports à éviter (souvent utilisés)
APP_FILE = "app.py"
CONFIG_FILE = Path(__file__).parent / ".port_config"


def get_local_ip() -> str:
    """Get local IP address (192.168.x.x or similar)."""
    try:
        # Create a socket to determine local IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        # Connect to an external IP (doesn't actually send data)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        return "127.0.0.1"


def get_public_ip() -> str:
    """Get public IP address via external API."""
    import urllib.request

    apis = [
        "https://ident.me",
        "https://api.ipify.org",
        "https://ifconfig.me/ip",
        "https://icanhazip.com"
    ]

    for api in apis:
        try:
            with urllib.request.urlopen(api, timeout=5) as response:
                ip = response.read().decode('utf-8').strip()
                # Validate IP format
                socket.inet_aton(ip)
                return ip
        except Exception:
            continue

    return "Non disponible"


def check_port_available(port: int) -> bool:
    """Check if a port is available."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.bind(("0.0.0.0", port))
        s.close()
        return True
    except OSError:
        return False


def find_available_port(start_port: int, excluded: list = None) -> int:
    """Find an available port starting from start_port, avoiding excluded ports."""
    if excluded is None:
        excluded = EXCLUDED_PORTS

    port = start_port
    max_attempts = 100

    for _ in range(max_attempts):
        if port not in excluded and check_port_available(port):
            return port
        port += 1

    # Si on n'a pas trouvé, chercher dans une autre plage
    for port in range(8000, 9000):
        if port not in excluded and check_port_available(port):
            return port

    return start_port  # Fallback


def save_port_config(port: int):
    """Save the last used port to config file."""
    try:
        with open(CONFIG_FILE, 'w') as f:
            f.write(str(port))
    except Exception:
        pass


def load_port_config() -> int:
    """Load the last used port from config file."""
    try:
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                return int(f.read().strip())
    except Exception:
        pass
    return DEFAULT_PORT


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Lanceur de l'application Mortalité France",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  python launcher.py                 # Port par défaut (8501)
  python launcher.py --port 8080     # Port personnalisé
  python launcher.py -p 9000         # Port personnalisé (forme courte)
  python launcher.py --no-browser    # Sans ouvrir le navigateur
        """
    )

    parser.add_argument(
        '-p', '--port',
        type=int,
        default=None,
        help=f"Port du serveur (défaut: {DEFAULT_PORT})"
    )

    parser.add_argument(
        '--no-browser',
        action='store_true',
        help="Ne pas ouvrir automatiquement le navigateur"
    )

    parser.add_argument(
        '--last-port',
        action='store_true',
        help="Utiliser le dernier port utilisé"
    )

    return parser.parse_args()


def print_banner():
    """Print application banner."""
    banner = """
    ╔═══════════════════════════════════════════════════════════════════╗
    ║                                                                   ║
    ║         📊  MORTALITÉ FRANCE - TABLEAU DE BORD  📊               ║
    ║                                                                   ║
    ║         Application d'analyse des données de décès INSEE         ║
    ║                                                                   ║
    ╚═══════════════════════════════════════════════════════════════════╝
    """
    print(banner)


def print_access_info(local_ip: str, public_ip: str, port: int):
    """Print access URLs."""
    print("\n" + "=" * 60)
    print("  🌐 URLS D'ACCÈS À L'APPLICATION")
    print("=" * 60)
    print(f"\n  📍 Accès local (cette machine):")
    print(f"     → http://localhost:{port}")
    print(f"     → http://127.0.0.1:{port}")

    print(f"\n  📡 Accès réseau local (même réseau WiFi/LAN):")
    print(f"     → http://{local_ip}:{port}")

    if public_ip != "Non disponible":
        print(f"\n  🌍 Accès externe (nécessite redirection de port):")
        print(f"     → http://{public_ip}:{port}")
        print(f"     ⚠️  Note: Nécessite configuration routeur (NAT/Port Forwarding)")
    else:
        print(f"\n  🌍 IP Publique: Non disponible (vérifiez votre connexion)")

    print("\n" + "=" * 60)
    print(f"  🔑 Mot de passe par défaut: mortalite2024")
    print("=" * 60)
    print("\n  ℹ️  Appuyez sur Ctrl+C pour arrêter le serveur\n")


def check_dependencies():
    """Check if required packages are installed."""
    required = ['streamlit', 'duckdb', 'pandas', 'plotly', 'folium', 'streamlit_folium']
    missing = []

    for package in required:
        try:
            __import__(package.replace('-', '_'))
        except ImportError:
            missing.append(package)

    if missing:
        print("⚠️  Packages manquants détectés:", ", ".join(missing))
        print("\n   Installez-les avec:")
        print(f"   pip install {' '.join(missing)}")
        print("\n   Ou utilisez le fichier requirements.txt:")
        print("   pip install -r requirements.txt\n")
        return False

    return True


def launch_streamlit(port: int, open_browser: bool = True):
    """Launch Streamlit server."""
    app_path = Path(__file__).parent / APP_FILE

    if not app_path.exists():
        print(f"❌ Erreur: Fichier {APP_FILE} non trouvé!")
        print(f"   Chemin attendu: {app_path}")
        sys.exit(1)

    # Build Streamlit command
    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_path),
        "--server.port", str(port),
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--theme.primaryColor", "#667eea",
        "--theme.backgroundColor", "#ffffff",
        "--theme.secondaryBackgroundColor", "#f0f2f6",
        "--theme.textColor", "#1a1a2e"
    ]

    print(f"\n🚀 Lancement du serveur Streamlit sur le port {port}...")
    print(f"   Commande: {' '.join(cmd[:6])}...\n")

    # Open browser after a delay
    if open_browser:
        def open_browser_delayed():
            time.sleep(3)
            webbrowser.open(f"http://localhost:{port}")

        import threading
        threading.Thread(target=open_browser_delayed, daemon=True).start()

    try:
        # Run Streamlit
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Stream output
        for line in process.stdout:
            print(line, end='')

    except KeyboardInterrupt:
        print("\n\n🛑 Arrêt du serveur...")
        process.terminate()
        process.wait(timeout=5)
        print("✅ Serveur arrêté proprement.")

    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        sys.exit(1)


def main():
    """Main launcher entry point."""
    # Parse command line arguments
    args = parse_arguments()

    print_banner()

    # Check dependencies
    print("🔍 Vérification des dépendances...")
    if not check_dependencies():
        print("❌ Installation des dépendances requise.")
        sys.exit(1)
    print("✅ Toutes les dépendances sont installées.\n")

    # Detect IPs
    print("🔍 Détection des adresses IP...")
    local_ip = get_local_ip()
    public_ip = get_public_ip()
    print(f"   IP locale: {local_ip}")
    print(f"   IP publique: {public_ip}")

    # Determine port to use
    if args.port:
        # Port spécifié en argument
        requested_port = args.port
        print(f"\n📌 Port demandé: {requested_port}")
    elif args.last_port:
        # Utiliser le dernier port
        requested_port = load_port_config()
        print(f"\n📌 Dernier port utilisé: {requested_port}")
    else:
        # Port par défaut
        requested_port = DEFAULT_PORT

    # Check if port is available
    if requested_port in EXCLUDED_PORTS:
        print(f"\n⚠️  Port {requested_port} est dans la liste des ports exclus (conflits connus)")
        port = find_available_port(DEFAULT_PORT)
        print(f"   Utilisation du port {port} à la place")
    elif not check_port_available(requested_port):
        print(f"\n⚠️  Port {requested_port} déjà utilisé, recherche d'un port disponible...")
        port = find_available_port(requested_port)
        print(f"   Utilisation du port {port}")
    else:
        port = requested_port
        print(f"\n✅ Port {port} disponible")

    # Save port for next time
    save_port_config(port)

    # Print access information
    print_access_info(local_ip, public_ip, port)

    # Launch server
    open_browser = not args.no_browser
    launch_streamlit(port, open_browser)


if __name__ == "__main__":
    main()
