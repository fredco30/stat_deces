#!/usr/bin/env python3
"""
Script de configuration réseau automatique pour l'application Mortalité France
Détecte automatiquement l'IP locale et configure Streamlit pour l'accès externe.

Compatible: Windows, Linux, macOS
"""

import socket
import subprocess
import sys
import platform
from pathlib import Path
import urllib.request
import json


def get_local_ip():
    """Détecte l'IP locale du PC (méthode universelle)."""
    try:
        # Méthode 1: Connexion socket (fonctionne partout)
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        return local_ip
    except Exception:
        pass

    # Méthode 2: Analyse des interfaces réseau
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        if local_ip and not local_ip.startswith("127."):
            return local_ip
    except Exception:
        pass

    return "127.0.0.1"


def get_public_ip():
    """Récupère l'IP publique via API externe."""
    apis = [
        "https://api.ipify.org?format=json",
        "https://ident.me",
        "https://ifconfig.me/ip",
        "https://icanhazip.com"
    ]

    for api in apis:
        try:
            with urllib.request.urlopen(api, timeout=5) as response:
                data = response.read().decode('utf-8').strip()
                if "ipify" in api:
                    ip = json.loads(data)['ip']
                else:
                    ip = data
                # Valider le format IP
                socket.inet_aton(ip)
                return ip
        except Exception:
            continue

    return "Non disponible"


def create_streamlit_config(local_ip):
    """Crée le fichier de configuration Streamlit."""
    config_dir = Path(__file__).parent / ".streamlit"
    config_dir.mkdir(exist_ok=True)

    config_file = config_dir / "config.toml"

    config_content = f"""[server]
# Configuration pour accès local et externe
address = "0.0.0.0"
port = 8501
headless = true
enableCORS = false
enableXsrfProtection = false

[browser]
gatherUsageStats = false
serverAddress = "{local_ip}"
serverPort = 8501

[theme]
primaryColor = "#667eea"
backgroundColor = "#ffffff"
secondaryBackgroundColor = "#f0f2f6"
textColor = "#1a1a2e"
"""

    with open(config_file, 'w', encoding='utf-8') as f:
        f.write(config_content)

    return config_file


def check_firewall_windows(port=8501):
    """Vérifie et configure le pare-feu Windows."""
    if platform.system() != "Windows":
        return True

    try:
        # Vérifier si la règle existe déjà
        result = subprocess.run(
            ['netsh', 'advfirewall', 'firewall', 'show', 'rule', 'name=Streamlit_8501'],
            capture_output=True,
            text=True
        )

        if "Streamlit_8501" in result.stdout:
            print("   ✅ Règle pare-feu déjà configurée")
            return True

        # Créer la règle
        print("   ⚠️  Règle pare-feu manquante. Tentative de création...")
        print("   ℹ️  Cela peut nécessiter les droits administrateur...")

        subprocess.run(
            [
                'netsh', 'advfirewall', 'firewall', 'add', 'rule',
                'name=Streamlit_8501',
                'dir=in',
                'action=allow',
                'protocol=TCP',
                f'localport={port}'
            ],
            check=False,
            capture_output=True
        )

        print("   ✅ Règle pare-feu créée avec succès")
        return True

    except Exception as e:
        print(f"   ⚠️  Impossible de configurer le pare-feu automatiquement: {e}")
        print(f"\n   📋 Veuillez exécuter manuellement en tant qu'administrateur:")
        print(f"   netsh advfirewall firewall add rule name=Streamlit_8501 dir=in action=allow protocol=TCP localport={port}")
        return False


def print_banner():
    """Affiche la bannière."""
    banner = """
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║     📊  CONFIGURATION RÉSEAU - MORTALITÉ FRANCE  📊              ║
║                                                                   ║
║          Configuration automatique de l'accès externe            ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
"""
    print(banner)


def print_network_info(local_ip, public_ip, port=8501):
    """Affiche les informations réseau."""
    print("\n" + "=" * 70)
    print("  🌐 CONFIGURATION RÉSEAU DÉTECTÉE")
    print("=" * 70)
    print(f"\n  💻 Système d'exploitation : {platform.system()} {platform.release()}")
    print(f"  📍 IP locale (LAN)        : {local_ip}")
    print(f"  🌍 IP publique (WAN)      : {public_ip}")
    print(f"  🔌 Port application       : {port}")
    print("\n" + "=" * 70)


def print_nat_instructions(local_ip, public_ip, port=8501):
    """Affiche les instructions de configuration NAT."""
    print("\n" + "=" * 70)
    print("  📋 CONFIGURATION DE VOTRE BOX INTERNET (NAT/PAT)")
    print("=" * 70)
    print("\n  Connectez-vous à votre box et créez/mettez à jour cette règle NAT:")
    print("\n  ┌────────────────────────────────────────────────────────────┐")
    print(f"  │  Nom de la règle  : stat_mortalité                        │")
    print(f"  │  Protocole        : TCP                                    │")
    print(f"  │  Port externe     : {port:<44} │")
    print(f"  │  IP interne       : {local_ip:<44} │")
    print(f"  │  Port interne     : {port:<44} │")
    print("  └────────────────────────────────────────────────────────────┘")
    print("\n  🔗 Interface de configuration de votre box:")
    print("     → http://192.168.1.254 (ou http://192.168.0.1)")
    print("     → Cherchez la section NAT/PAT ou Redirection de ports")
    print("\n" + "=" * 70)


def print_access_urls(local_ip, public_ip, port=8501):
    """Affiche les URLs d'accès."""
    print("\n" + "=" * 70)
    print("  🌐 URLS D'ACCÈS À L'APPLICATION")
    print("=" * 70)

    print(f"\n  📍 Accès local (sur ce PC):")
    print(f"     → http://localhost:{port}")
    print(f"     → http://127.0.0.1:{port}")

    print(f"\n  📡 Accès réseau local (même WiFi/LAN):")
    print(f"     → http://{local_ip}:{port}")

    if public_ip != "Non disponible":
        print(f"\n  🌍 Accès externe (depuis Internet):")
        print(f"     → http://{public_ip}:{port}")
        print(f"     ⚠️  Nécessite la configuration NAT ci-dessus")

    print("\n  🔑 Mot de passe par défaut : mortalite2024")
    print("\n" + "=" * 70)


def save_network_info(local_ip, public_ip, port=8501):
    """Sauvegarde les informations réseau dans un fichier."""
    info_file = Path(__file__).parent / "network_info.txt"

    with open(info_file, 'w', encoding='utf-8') as f:
        f.write("=" * 70 + "\n")
        f.write("INFORMATIONS RÉSEAU - MORTALITÉ FRANCE\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Date de configuration : {Path(__file__).stat().st_mtime}\n")
        f.write(f"Système d'exploitation : {platform.system()} {platform.release()}\n")
        f.write(f"IP locale (LAN) : {local_ip}\n")
        f.write(f"IP publique (WAN) : {public_ip}\n")
        f.write(f"Port : {port}\n\n")
        f.write("=" * 70 + "\n")
        f.write("URLS D'ACCÈS\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Local : http://localhost:{port}\n")
        f.write(f"Réseau local : http://{local_ip}:{port}\n")
        if public_ip != "Non disponible":
            f.write(f"Externe : http://{public_ip}:{port}\n\n")
        f.write("=" * 70 + "\n")
        f.write("CONFIGURATION NAT À CRÉER DANS VOTRE BOX\n")
        f.write("=" * 70 + "\n\n")
        f.write(f"Protocole : TCP\n")
        f.write(f"Port externe : {port}\n")
        f.write(f"IP interne : {local_ip}\n")
        f.write(f"Port interne : {port}\n")

    return info_file


def main():
    """Point d'entrée principal."""
    print_banner()

    print("🔍 Détection de la configuration réseau...\n")

    # Détecter les IPs
    local_ip = get_local_ip()
    print(f"   ✅ IP locale détectée : {local_ip}")

    public_ip = get_public_ip()
    print(f"   ✅ IP publique détectée : {public_ip}")

    # Créer la configuration Streamlit
    print("\n⚙️  Configuration de Streamlit...\n")
    config_file = create_streamlit_config(local_ip)
    print(f"   ✅ Fichier créé : {config_file}")

    # Configurer le pare-feu (Windows uniquement)
    if platform.system() == "Windows":
        print("\n🔥 Configuration du pare-feu Windows...\n")
        check_firewall_windows()

    # Sauvegarder les informations
    print("\n💾 Sauvegarde des informations réseau...\n")
    info_file = save_network_info(local_ip, public_ip)
    print(f"   ✅ Fichier créé : {info_file}")

    # Afficher les informations
    print_network_info(local_ip, public_ip)
    print_nat_instructions(local_ip, public_ip)
    print_access_urls(local_ip, public_ip)

    print("\n✅ Configuration terminée !\n")
    print("📋 Prochaines étapes :")
    print("   1. Configurez la règle NAT dans votre box (voir ci-dessus)")
    print("   2. Lancez l'application avec : python start.py")
    print("   3. Accédez à l'application via les URLs ci-dessus\n")

    # Demander si on doit lancer l'application
    try:
        response = input("Voulez-vous lancer l'application maintenant ? (o/n) : ")
        if response.lower() in ['o', 'y', 'oui', 'yes']:
            print("\n🚀 Lancement de l'application...\n")
            launcher_path = Path(__file__).parent / "launcher.py"
            if launcher_path.exists():
                subprocess.run([sys.executable, str(launcher_path)])
            else:
                print(f"❌ Fichier launcher.py non trouvé : {launcher_path}")
    except KeyboardInterrupt:
        print("\n\n👋 Configuration sauvegardée. À bientôt !")
        sys.exit(0)


if __name__ == "__main__":
    main()
