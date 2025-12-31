#!/usr/bin/env python3
"""
Intelligent Launcher for French Mortality Data Application
Detects IPs, displays access URLs, and launches Streamlit server.
"""

import subprocess
import socket
import sys
import os
import time
import webbrowser
from pathlib import Path

# Configuration
PORT = 5173
APP_FILE = "app.py"


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


def find_available_port(start_port: int) -> int:
    """Find an available port starting from start_port."""
    port = start_port
    while not check_port_available(port) and port < start_port + 100:
        port += 1
    return port


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

    # Find available port
    port = PORT
    if not check_port_available(port):
        print(f"\n⚠️  Port {port} déjà utilisé, recherche d'un port disponible...")
        port = find_available_port(port)
        print(f"   Utilisation du port {port}")

    # Print access information
    print_access_info(local_ip, public_ip, port)

    # Launch server
    launch_streamlit(port)


if __name__ == "__main__":
    main()
