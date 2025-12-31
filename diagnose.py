#!/usr/bin/env python3
"""
Script de diagnostic réseau ultra-détaillé
Teste toutes les couches pour identifier le problème de connexion
"""

import socket
import subprocess
import sys
import platform
import urllib.request
import time
from pathlib import Path
from datetime import datetime


class DiagnosticLogger:
    """Logger avec timestamps et couleurs."""

    def __init__(self):
        self.log_file = Path(__file__).parent / f"diagnostic_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.start_time = time.time()

    def log(self, message, level="INFO"):
        """Log un message avec timestamp."""
        timestamp = time.time() - self.start_time
        log_line = f"[{timestamp:8.2f}s] [{level:5s}] {message}"
        print(log_line)

        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(log_line + '\n')

    def section(self, title):
        """Log une section."""
        separator = "=" * 80
        self.log("")
        self.log(separator)
        self.log(f"  {title}")
        self.log(separator)

    def success(self, message):
        """Log un succès."""
        self.log(f"✅ {message}", "OK")

    def warning(self, message):
        """Log un avertissement."""
        self.log(f"⚠️  {message}", "WARN")

    def error(self, message):
        """Log une erreur."""
        self.log(f"❌ {message}", "ERROR")

    def info(self, message):
        """Log une information."""
        self.log(f"ℹ️  {message}", "INFO")

    def test(self, test_name):
        """Log le début d'un test."""
        self.log(f"🧪 Test: {test_name}", "TEST")


logger = DiagnosticLogger()


def run_command(cmd, shell=False, timeout=10):
    """Exécute une commande et retourne le résultat."""
    try:
        logger.info(f"Exécution: {cmd if isinstance(cmd, str) else ' '.join(cmd)}")
        result = subprocess.run(
            cmd,
            shell=shell,
            capture_output=True,
            text=True,
            timeout=timeout
        )
        logger.info(f"Code retour: {result.returncode}")
        if result.stdout:
            logger.info(f"STDOUT:\n{result.stdout}")
        if result.stderr:
            logger.warning(f"STDERR:\n{result.stderr}")
        return result
    except subprocess.TimeoutExpired:
        logger.error(f"Timeout après {timeout}s")
        return None
    except Exception as e:
        logger.error(f"Erreur d'exécution: {e}")
        return None


def test_1_system_info():
    """Test 1: Informations système."""
    logger.section("TEST 1: INFORMATIONS SYSTÈME")

    logger.info(f"OS: {platform.system()} {platform.release()}")
    logger.info(f"Version: {platform.version()}")
    logger.info(f"Architecture: {platform.machine()}")
    logger.info(f"Python: {sys.version}")
    logger.info(f"Hostname: {socket.gethostname()}")

    logger.success("Informations système collectées")


def test_2_network_interfaces():
    """Test 2: Interfaces réseau."""
    logger.section("TEST 2: INTERFACES RÉSEAU")

    if platform.system() == "Windows":
        result = run_command("ipconfig /all", shell=True)
        if result and result.returncode == 0:
            logger.success("Configuration réseau récupérée")
        else:
            logger.error("Impossible de récupérer ipconfig")
    else:
        result = run_command(["ip", "addr", "show"])
        if result and result.returncode == 0:
            logger.success("Interfaces réseau récupérées")
        else:
            logger.error("Impossible de récupérer les interfaces")


def test_3_local_ip():
    """Test 3: Détection IP locale."""
    logger.section("TEST 3: DÉTECTION IP LOCALE")

    try:
        # Méthode 1: Socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(2)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
        logger.success(f"IP locale (socket): {local_ip}")

        # Méthode 2: Hostname
        hostname_ip = socket.gethostbyname(socket.gethostname())
        logger.info(f"IP locale (hostname): {hostname_ip}")

        return local_ip
    except Exception as e:
        logger.error(f"Impossible de détecter l'IP locale: {e}")
        return None


def test_4_public_ip():
    """Test 4: Détection IP publique."""
    logger.section("TEST 4: DÉTECTION IP PUBLIQUE")

    apis = [
        ("https://api.ipify.org", "text"),
        ("https://ident.me", "text"),
        ("https://ifconfig.me/ip", "text"),
        ("https://icanhazip.com", "text")
    ]

    for api, format_type in apis:
        try:
            logger.test(f"Test API: {api}")
            with urllib.request.urlopen(api, timeout=5) as response:
                ip = response.read().decode('utf-8').strip()
                logger.success(f"IP publique: {ip}")
                return ip
        except Exception as e:
            logger.error(f"Échec {api}: {e}")

    logger.error("Impossible de détecter l'IP publique")
    return None


def test_5_port_listening():
    """Test 5: Vérifier si le port 8501 écoute."""
    logger.section("TEST 5: PORT 8501 - ÉCOUTE")

    port = 8501

    # Test avec netstat
    logger.test("Vérification avec netstat")
    if platform.system() == "Windows":
        result = run_command("netstat -an | findstr :8501", shell=True)
    else:
        result = run_command("netstat -tuln | grep :8501", shell=True)

    if result and result.returncode == 0 and result.stdout:
        logger.success(f"Port {port} trouvé dans netstat:\n{result.stdout}")
    else:
        logger.error(f"Port {port} non trouvé dans netstat")

    # Test avec socket
    logger.test("Vérification avec socket bind")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        result = s.connect_ex(('127.0.0.1', port))
        s.close()

        if result == 0:
            logger.success(f"Port {port} est OUVERT sur localhost")
            return True
        else:
            logger.error(f"Port {port} est FERMÉ sur localhost (code: {result})")
            return False
    except Exception as e:
        logger.error(f"Erreur lors du test socket: {e}")
        return False


def test_6_process_listening():
    """Test 6: Processus écoutant sur le port 8501."""
    logger.section("TEST 6: PROCESSUS UTILISANT LE PORT 8501")

    if platform.system() == "Windows":
        result = run_command("netstat -ano | findstr :8501", shell=True)
        if result and result.stdout:
            logger.info("Processus trouvés:")
            logger.info(result.stdout)

            # Essayer de trouver les PIDs
            for line in result.stdout.split('\n'):
                if ':8501' in line:
                    parts = line.split()
                    if parts:
                        pid = parts[-1]
                        logger.info(f"PID trouvé: {pid}")

                        # Trouver le nom du processus
                        task_result = run_command(f'tasklist /FI "PID eq {pid}"', shell=True)
                        if task_result and task_result.stdout:
                            logger.info(f"Processus:\n{task_result.stdout}")
        else:
            logger.error("Aucun processus n'écoute sur le port 8501")
    else:
        result = run_command("lsof -i :8501", shell=True)
        if result and result.stdout:
            logger.success(f"Processus trouvés:\n{result.stdout}")
        else:
            logger.error("Aucun processus n'écoute sur le port 8501")


def test_7_firewall_rules():
    """Test 7: Règles de pare-feu."""
    logger.section("TEST 7: PARE-FEU WINDOWS")

    if platform.system() != "Windows":
        logger.info("Test pare-feu uniquement sur Windows")
        return

    # Vérifier les règles du pare-feu
    logger.test("Règles pare-feu pour le port 8501")
    result = run_command(
        'netsh advfirewall firewall show rule name=all | findstr /C:"8501" /C:"Streamlit"',
        shell=True,
        timeout=30
    )

    if result and result.stdout:
        logger.success(f"Règles trouvées:\n{result.stdout}")
    else:
        logger.warning("Aucune règle pare-feu pour le port 8501")
        logger.info("Tentative de création d'une règle...")

        # Tenter de créer une règle
        create_result = run_command(
            'netsh advfirewall firewall add rule name="Streamlit_8501_Diagnostic" dir=in action=allow protocol=TCP localport=8501',
            shell=True
        )

        if create_result and create_result.returncode == 0:
            logger.success("Règle pare-feu créée avec succès")
        else:
            logger.error("Impossible de créer la règle (privilèges admin requis?)")

    # Vérifier l'état du pare-feu
    logger.test("État du pare-feu")
    result = run_command('netsh advfirewall show allprofiles state', shell=True)
    if result and result.stdout:
        logger.info(f"État du pare-feu:\n{result.stdout}")


def test_8_local_connection():
    """Test 8: Test de connexion locale."""
    logger.section("TEST 8: CONNEXION LOCALE (localhost:8501)")

    test_urls = [
        "http://localhost:8501",
        "http://127.0.0.1:8501",
    ]

    for url in test_urls:
        logger.test(f"Test: {url}")
        try:
            with urllib.request.urlopen(url, timeout=5) as response:
                status = response.status
                logger.success(f"Connexion réussie! Status: {status}")
                logger.info(f"Headers:\n{response.headers}")
        except urllib.error.URLError as e:
            logger.error(f"Erreur de connexion: {e}")
        except Exception as e:
            logger.error(f"Erreur inattendue: {e}")


def test_9_lan_connection(local_ip):
    """Test 9: Test de connexion sur l'IP LAN."""
    logger.section("TEST 9: CONNEXION RÉSEAU LOCAL (LAN)")

    if not local_ip:
        logger.error("IP locale non disponible")
        return

    url = f"http://{local_ip}:8501"
    logger.test(f"Test: {url}")

    try:
        with urllib.request.urlopen(url, timeout=5) as response:
            status = response.status
            logger.success(f"Connexion LAN réussie! Status: {status}")
    except urllib.error.URLError as e:
        logger.error(f"Erreur de connexion LAN: {e}")
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")


def test_10_streamlit_config():
    """Test 10: Configuration Streamlit."""
    logger.section("TEST 10: CONFIGURATION STREAMLIT")

    config_file = Path(__file__).parent / ".streamlit" / "config.toml"

    logger.test(f"Vérification du fichier: {config_file}")

    if config_file.exists():
        logger.success("Fichier config.toml trouvé")
        with open(config_file, 'r', encoding='utf-8') as f:
            content = f.read()
            logger.info(f"Contenu:\n{content}")
    else:
        logger.error("Fichier config.toml non trouvé")
        logger.info(f"Chemin attendu: {config_file}")


def test_11_dns_resolution():
    """Test 11: Résolution DNS et connectivité externe."""
    logger.section("TEST 11: RÉSOLUTION DNS ET CONNECTIVITÉ")

    test_hosts = [
        "google.com",
        "8.8.8.8",
    ]

    for host in test_hosts:
        logger.test(f"Test résolution: {host}")
        try:
            ip = socket.gethostbyname(host)
            logger.success(f"{host} résolu en {ip}")
        except Exception as e:
            logger.error(f"Impossible de résoudre {host}: {e}")


def test_12_routing_table():
    """Test 12: Table de routage."""
    logger.section("TEST 12: TABLE DE ROUTAGE")

    if platform.system() == "Windows":
        result = run_command("route print", shell=True)
    else:
        result = run_command("ip route show", shell=True)

    if result and result.returncode == 0:
        logger.success("Table de routage récupérée")
    else:
        logger.error("Impossible de récupérer la table de routage")


def test_13_gateway_ping():
    """Test 13: Ping de la passerelle."""
    logger.section("TEST 13: PING PASSERELLE")

    if platform.system() == "Windows":
        # Trouver la passerelle par défaut
        result = run_command("ipconfig | findstr /C:\"Passerelle\"", shell=True)
        if result and result.stdout:
            logger.info(f"Passerelle trouvée:\n{result.stdout}")

            # Extraire l'IP de la passerelle (192.168.1.254)
            lines = result.stdout.split('\n')
            for line in lines:
                if '192.168' in line or '10.' in line:
                    parts = line.split(':')
                    if len(parts) > 1:
                        gateway = parts[1].strip()
                        logger.test(f"Ping gateway: {gateway}")
                        ping_result = run_command(f"ping -n 4 {gateway}", shell=True)
                        if ping_result and ping_result.returncode == 0:
                            logger.success(f"Ping gateway {gateway} réussi")
                        else:
                            logger.error(f"Ping gateway {gateway} échoué")
                        break


def test_14_binding_test():
    """Test 14: Test de binding sur 0.0.0.0."""
    logger.section("TEST 14: TEST DE BINDING SUR 0.0.0.0:8501")

    logger.test("Tentative de binding sur 0.0.0.0:8501")

    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(2)

        # Tester si on peut binder
        try:
            s.bind(('0.0.0.0', 8501))
            logger.warning("Port 8501 est LIBRE - L'application n'est PAS lancée!")
            s.close()
        except OSError as e:
            if e.errno == 10048 or e.errno == 98:  # Address already in use
                logger.success("Port 8501 est OCCUPÉ - L'application EST lancée")
            else:
                logger.error(f"Erreur de binding: {e}")

    except Exception as e:
        logger.error(f"Erreur lors du test de binding: {e}")


def generate_summary(local_ip, public_ip):
    """Génère un résumé du diagnostic."""
    logger.section("RÉSUMÉ DU DIAGNOSTIC")

    logger.info("=== RÉSULTATS ===")
    logger.info(f"IP Locale: {local_ip or 'NON DÉTECTÉE'}")
    logger.info(f"IP Publique: {public_ip or 'NON DÉTECTÉE'}")
    logger.info("")
    logger.info("=== CONFIGURATION NAT RECOMMANDÉE ===")
    logger.info(f"Protocole: TCP")
    logger.info(f"Port externe: 8501")
    logger.info(f"IP interne: {local_ip or '???'}")
    logger.info(f"Port interne: 8501")
    logger.info("")
    logger.info(f"=== FICHIER DE LOG ===")
    logger.info(f"Log détaillé sauvegardé dans: {logger.log_file}")
    logger.info("")
    logger.info("=== PROCHAINES ÉTAPES ===")
    logger.info("1. Vérifiez que l'application est lancée (Test 5)")
    logger.info("2. Vérifiez le pare-feu Windows (Test 7)")
    logger.info("3. Vérifiez la règle NAT de votre box")
    logger.info("4. Consultez le fichier de log pour plus de détails")


def main():
    """Point d'entrée principal."""
    print("""
╔═══════════════════════════════════════════════════════════════════╗
║                                                                   ║
║         🔍  DIAGNOSTIC RÉSEAU ULTRA-DÉTAILLÉ  🔍                 ║
║                                                                   ║
║              Application Mortalité France                        ║
║                                                                   ║
╚═══════════════════════════════════════════════════════════════════╝
""")

    logger.info("Début du diagnostic")
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    try:
        # Exécuter tous les tests
        test_1_system_info()
        test_2_network_interfaces()
        local_ip = test_3_local_ip()
        public_ip = test_4_public_ip()
        test_5_port_listening()
        test_6_process_listening()
        test_7_firewall_rules()
        test_8_local_connection()
        test_9_lan_connection(local_ip)
        test_10_streamlit_config()
        test_11_dns_resolution()
        test_12_routing_table()
        test_13_gateway_ping()
        test_14_binding_test()

        # Résumé
        generate_summary(local_ip, public_ip)

        logger.success("Diagnostic terminé!")
        logger.info(f"Temps total: {time.time() - logger.start_time:.2f}s")

        print(f"\n{'='*70}")
        print(f"📄 FICHIER DE LOG: {logger.log_file}")
        print(f"{'='*70}\n")

        print("Appuyez sur Entrée pour quitter...")
        input()

    except KeyboardInterrupt:
        logger.warning("Diagnostic interrompu par l'utilisateur")
    except Exception as e:
        logger.error(f"Erreur fatale: {e}")
        import traceback
        logger.error(traceback.format_exc())


if __name__ == "__main__":
    main()
