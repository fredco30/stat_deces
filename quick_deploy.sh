#!/bin/bash

# Script de déploiement rapide - à exécuter depuis le dossier stat_deces
# Usage: bash quick_deploy.sh

set -e

echo "🚀 Déploiement rapide de stat_deces"
echo "===================================="
echo ""

# Obtenir le chemin absolu du dossier actuel
APP_DIR=$(pwd)
echo "📁 Dossier de l'application: $APP_DIR"
echo ""

# 1. Mise à jour système et installation des dépendances
echo "📦 Installation des dépendances..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git nginx ufw curl

# 2. Créer environnement virtuel
echo "🐍 Configuration de l'environnement Python..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install streamlit pandas duckdb plotly openpyxl

# 3. Initialiser la base
echo "🗄️  Initialisation de la base de données..."
python3 -c "import etl_utils; etl_utils.initialize_database()"

# 4. Créer le service systemd
echo "⚙️  Configuration du service systemd..."
sudo tee /etc/systemd/system/streamlit-stat-deces.service > /dev/null << EOF
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

sudo systemctl daemon-reload
sudo systemctl enable streamlit-stat-deces
sudo systemctl start streamlit-stat-deces

# 5. Configuration Nginx
echo "🌐 Configuration de Nginx..."
sudo tee /etc/nginx/sites-available/stat-deces > /dev/null << 'EOF'
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

sudo ln -sf /etc/nginx/sites-available/stat-deces /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

# 6. Configuration firewall
echo "🔥 Configuration du firewall..."
sudo ufw allow 22/tcp
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw --force enable

# 7. Résultat
echo ""
echo "✅ INSTALLATION TERMINÉE!"
echo "========================"
echo ""
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo "🌍 Votre application est accessible via:"
echo "   http://$PUBLIC_IP"
echo ""
echo "📋 Vérification des services:"
sudo systemctl status streamlit-stat-deces --no-pager | grep Active
sudo systemctl status nginx --no-pager | grep Active
echo ""
echo "📝 Commandes utiles:"
echo "   • Logs:      sudo journalctl -u streamlit-stat-deces -f"
echo "   • Redémarrer: sudo systemctl restart streamlit-stat-deces"
echo ""
