#!/bin/bash
set -e

echo "🚀 Installation stat_deces (Port 8501 - SANS Nginx)"
echo "===================================================="

APP_DIR=$(pwd)
echo "📁 Dossier: $APP_DIR"

# 1. Installation Python
echo "📦 Installation Python..."
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# 2. Environnement virtuel
echo "🐍 Environnement virtuel..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install streamlit pandas duckdb plotly openpyxl

# 3. Base de données
echo "🗄️  Initialisation base de données..."
python3 -c "import etl_utils; etl_utils.initialize_database()"

# 4. Service systemd (Port 8501 exposé publiquement)
echo "⚙️  Configuration service systemd..."
sudo tee /etc/systemd/system/streamlit-stat-deces.service > /dev/null << EOFSERVICE
[Unit]
Description=Streamlit Stat Deces Application
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/venv/bin"
ExecStart=$APP_DIR/venv/bin/streamlit run app.py --server.port=8501 --server.address=0.0.0.0 --server.headless=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOFSERVICE

sudo systemctl daemon-reload
sudo systemctl enable streamlit-stat-deces
sudo systemctl start streamlit-stat-deces

# 5. Firewall
echo "🔥 Configuration firewall..."
sudo ufw allow 8501/tcp

# 6. Affichage résultat
echo ""
echo "✅ INSTALLATION TERMINÉE!"
echo "========================"
echo ""
PUBLIC_IP=$(curl -s ifconfig.me 2>/dev/null || echo "51.210.8.158")
echo "🌍 Votre application stat_deces est accessible via:"
echo ""
echo "   http://$PUBLIC_IP:8501"
echo "   http://51.210.8.158:8501"
echo ""
echo "📋 Statut du service:"
sudo systemctl status streamlit-stat-deces --no-pager -l | head -15
echo ""
echo "📝 Commandes utiles:"
echo "   • Voir les logs:  sudo journalctl -u streamlit-stat-deces -f"
echo "   • Redémarrer:     sudo systemctl restart streamlit-stat-deces"
echo "   • Arrêter:        sudo systemctl stop streamlit-stat-deces"
echo "   • Statut:         sudo systemctl status streamlit-stat-deces"
echo ""
