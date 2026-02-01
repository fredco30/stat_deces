#!/bin/bash

# Script de déploiement automatique pour stat_deces sur OVH
# Usage: bash deploy.sh

set -e  # Arrêter en cas d'erreur

echo "================================================"
echo "🚀 Déploiement de stat_deces sur serveur OVH"
echo "================================================"
echo ""

# Couleurs pour les messages
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Fonction pour afficher les étapes
step() {
    echo -e "${GREEN}[ÉTAPE]${NC} $1"
}

error() {
    echo -e "${RED}[ERREUR]${NC} $1"
    exit 1
}

warning() {
    echo -e "${YELLOW}[ATTENTION]${NC} $1"
}

# Vérifier si on est root
if [ "$EUID" -ne 0 ]; then
    warning "Ce script devrait être exécuté en tant que root"
    echo "Voulez-vous continuer quand même? (y/n)"
    read -r response
    if [[ ! "$response" =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# ÉTAPE 1: Mise à jour du système
step "1/9 - Mise à jour du système..."
apt update && apt upgrade -y || error "Échec de la mise à jour"

# ÉTAPE 2: Installation des dépendances
step "2/9 - Installation des dépendances système..."
apt install -y python3 python3-pip python3-venv git nginx ufw curl || error "Échec de l'installation des dépendances"

# Vérifier les versions
echo "Python version: $(python3 --version)"
echo "Git version: $(git --version)"
echo "Nginx version: $(nginx -v 2>&1)"

# ÉTAPE 3: Créer l'environnement virtuel
step "3/9 - Configuration de l'environnement Python..."
APP_DIR="$HOME/stat_deces"

if [ -d "$APP_DIR" ]; then
    warning "Le dossier $APP_DIR existe déjà"
    echo "Voulez-vous le supprimer et recommencer? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        rm -rf "$APP_DIR"
    fi
fi

# Si le dossier n'existe pas, on est dans le process d'installation initiale
if [ ! -d "$APP_DIR" ]; then
    echo "Le repository sera cloné dans: $APP_DIR"
    echo "Note: Assurez-vous que cette machine a accès au repository Git"

    # Créer le dossier
    mkdir -p "$APP_DIR"
    cd "$APP_DIR"

    # Initialiser un repo git vide (l'utilisateur devra push depuis son PC)
    warning "Vous devrez transférer les fichiers de votre application ici"
    echo "Option 1: Utilisez 'git clone' si votre repo est accessible"
    echo "Option 2: Utilisez 'scp' pour copier les fichiers depuis votre PC"
    echo ""
    echo "Voulez-vous cloner depuis Git maintenant? (y/n)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        echo "Entrez l'URL du repository (ex: https://github.com/fredco30/stat_deces.git):"
        read -r repo_url
        git clone "$repo_url" . || error "Échec du clonage"

        echo "Quelle branche voulez-vous utiliser? (défaut: claude/mortality-trends-tab-hyDoe)"
        read -r branch
        branch=${branch:-claude/mortality-trends-tab-hyDoe}
        git checkout "$branch" || warning "Branche $branch non trouvée, utilisation de la branche actuelle"
    else
        echo "Veuillez transférer les fichiers avant de continuer"
        echo "Exemple depuis votre PC local:"
        echo "  scp -r /path/to/stat_deces/* root@YOUR_SERVER_IP:~/stat_deces/"
        echo ""
        echo "Appuyez sur Entrée quand les fichiers sont transférés..."
        read
    fi
else
    cd "$APP_DIR"
fi

# Créer l'environnement virtuel
if [ ! -d "venv" ]; then
    python3 -m venv venv || error "Échec de la création de l'environnement virtuel"
fi

# Activer et installer les packages
step "4/9 - Installation des packages Python..."
source venv/bin/activate
pip install --upgrade pip
pip install streamlit pandas duckdb plotly openpyxl || error "Échec de l'installation des packages Python"

# ÉTAPE 5: Initialiser la base de données
step "5/9 - Initialisation de la base de données..."
if [ -f "etl_utils.py" ]; then
    python3 -c "import etl_utils; etl_utils.initialize_database()" || warning "Échec de l'initialisation de la base"
    if [ -f "deces.db" ]; then
        echo "✓ Base de données créée: deces.db"
        ls -lh deces.db
    fi
else
    warning "etl_utils.py non trouvé, base de données non initialisée"
fi

# ÉTAPE 6: Configurer systemd
step "6/9 - Configuration du service systemd..."
cat > /etc/systemd/system/streamlit-stat-deces.service << EOF
[Unit]
Description=Streamlit Stat Deces Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/streamlit run app.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable streamlit-stat-deces
systemctl start streamlit-stat-deces || warning "Échec du démarrage du service (normal si app.py n'existe pas encore)"

# ÉTAPE 7: Configurer Nginx
step "7/9 - Configuration de Nginx..."
cat > /etc/nginx/sites-available/stat-deces << 'EOF'
server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 86400;
    }
}
EOF

# Activer la configuration
ln -sf /etc/nginx/sites-available/stat-deces /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default

# Tester la configuration
nginx -t || error "Configuration Nginx invalide"
systemctl restart nginx

# ÉTAPE 8: Configurer le firewall
step "8/9 - Configuration du firewall..."
ufw allow 22/tcp  # SSH
ufw allow 80/tcp  # HTTP
ufw allow 443/tcp # HTTPS
ufw --force enable

# ÉTAPE 9: Afficher les informations de connexion
step "9/9 - Installation terminée!"
echo ""
echo "================================================"
echo "✅ INSTALLATION RÉUSSIE!"
echo "================================================"
echo ""
echo "📍 Répertoire de l'application: $APP_DIR"
echo ""
echo "🌐 Votre application est accessible via:"
PUBLIC_IP=$(curl -s ifconfig.me || hostname -I | awk '{print $1}')
echo "   http://$PUBLIC_IP"
echo ""
echo "🔍 Commandes utiles:"
echo "   • Voir les logs:     sudo journalctl -u streamlit-stat-deces -f"
echo "   • Redémarrer:        sudo systemctl restart streamlit-stat-deces"
echo "   • Statut du service: sudo systemctl status streamlit-stat-deces"
echo "   • Mettre à jour:     cd $APP_DIR && git pull && sudo systemctl restart streamlit-stat-deces"
echo ""
echo "🔧 État des services:"
systemctl is-active streamlit-stat-deces && echo "   • Streamlit: ✓ ACTIF" || echo "   • Streamlit: ✗ INACTIF"
systemctl is-active nginx && echo "   • Nginx:     ✓ ACTIF" || echo "   • Nginx:     ✗ INACTIF"
echo ""
echo "📖 Pour plus d'informations, consultez DEPLOYMENT_GUIDE.md"
echo ""
