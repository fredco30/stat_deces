# Guide de Déploiement sur Serveur OVH

## 📋 Prérequis
- Un serveur OVH (VPS ou Dedicated)
- Accès SSH au serveur
- Ubuntu/Debian recommandé

---

## 🔐 ÉTAPE 1: Connexion au serveur OVH

### Obtenir vos informations de connexion

1. **Connectez-vous à votre espace client OVH**: https://www.ovh.com/manager/
2. Allez dans **"Bare Metal Cloud"** > **"Serveurs dédiés"** ou **"VPS"**
3. Cliquez sur votre serveur
4. Notez:
   - **Adresse IP**: affichée en haut (ex: `51.xx.xx.xx`)
   - **Nom d'utilisateur**: généralement `root` ou `ubuntu`
   - **Mot de passe**: si vous l'avez perdu, utilisez le mode "rescue" pour le réinitialiser

### Se connecter via SSH

**Windows (PowerShell ou CMD):**
```bash
ssh root@VOTRE_IP
# Exemple: ssh root@51.68.45.123
```

**Linux/Mac (Terminal):**
```bash
ssh root@VOTRE_IP
```

**Acceptez le fingerprint** en tapant `yes` quand demandé.

---

## 🔧 ÉTAPE 2: Installation des dépendances système

Une fois connecté au serveur, exécutez ces commandes:

```bash
# Mettre à jour les packages
sudo apt update && sudo apt upgrade -y

# Installer Python 3, pip, git et nginx
sudo apt install -y python3 python3-pip python3-venv git nginx

# Vérifier l'installation
python3 --version  # Doit afficher Python 3.8+
git --version
nginx -v
```

---

## 📥 ÉTAPE 3: Cloner le repository

```bash
# Aller dans le répertoire home
cd ~

# Cloner votre repository
git clone https://github.com/fredco30/stat_deces.git

# Aller dans le dossier
cd stat_deces

# Vérifier la branche
git branch -a
git checkout claude/mortality-trends-tab-hyDoe
```

---

## 🐍 ÉTAPE 4: Configuration de l'environnement Python

```bash
# Créer un environnement virtuel
python3 -m venv venv

# Activer l'environnement virtuel
source venv/bin/activate

# Installer les dépendances
pip install --upgrade pip
pip install streamlit pandas duckdb plotly openpyxl

# Vérifier l'installation
streamlit --version
```

---

## 🗄️ ÉTAPE 5: Initialiser la base de données

```bash
# Dans le dossier stat_deces avec l'environnement activé
python3 -c "import etl_utils; etl_utils.initialize_database()"

# Vérifier que deces.db a été créé
ls -lh deces.db
```

---

## 🚀 ÉTAPE 6: Configurer Streamlit comme service systemd

Créez un fichier de service pour que Streamlit démarre automatiquement:

```bash
sudo nano /etc/systemd/system/streamlit-stat-deces.service
```

Copiez ce contenu (remplacez `/root` par votre répertoire home si différent):

```ini
[Unit]
Description=Streamlit Stat Deces Application
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/stat_deces
Environment="PATH=/root/stat_deces/venv/bin"
ExecStart=/root/stat_deces/venv/bin/streamlit run app.py --server.port=8501 --server.address=127.0.0.1 --server.headless=true
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Sauvegardez**: `Ctrl+X`, puis `Y`, puis `Entrée`

Activez et démarrez le service:

```bash
# Recharger systemd
sudo systemctl daemon-reload

# Activer le service au démarrage
sudo systemctl enable streamlit-stat-deces

# Démarrer le service
sudo systemctl start streamlit-stat-deces

# Vérifier le statut
sudo systemctl status streamlit-stat-deces
```

Si tout fonctionne, vous devriez voir "active (running)" en vert.

---

## 🌐 ÉTAPE 7: Configurer Nginx comme reverse proxy

Nginx va exposer votre application sur le port 80 (HTTP).

```bash
# Créer la configuration Nginx
sudo nano /etc/nginx/sites-available/stat-deces
```

Copiez cette configuration:

```nginx
server {
    listen 80;
    server_name _;  # Accepte toutes les connexions

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
```

**Sauvegardez**: `Ctrl+X`, puis `Y`, puis `Entrée`

Activez la configuration:

```bash
# Créer un lien symbolique
sudo ln -s /etc/nginx/sites-available/stat-deces /etc/nginx/sites-enabled/

# Supprimer la config par défaut (optionnel)
sudo rm /etc/nginx/sites-enabled/default

# Tester la configuration
sudo nginx -t

# Recharger Nginx
sudo systemctl restart nginx
```

---

## 🔥 ÉTAPE 8: Configurer le firewall

```bash
# Autoriser SSH (important pour ne pas vous bloquer!)
sudo ufw allow 22/tcp

# Autoriser HTTP
sudo ufw allow 80/tcp

# Autoriser HTTPS (si vous configurez SSL plus tard)
sudo ufw allow 443/tcp

# Activer le firewall
sudo ufw --force enable

# Vérifier le statut
sudo ufw status
```

---

## 🌍 ÉTAPE 9: Accéder à votre application

### Trouver votre IP publique

Depuis votre serveur:
```bash
curl ifconfig.me
# OU
hostname -I | awk '{print $1}'
```

### URL d'accès

Votre application est maintenant accessible via:

```
http://VOTRE_IP_PUBLIQUE
```

**Exemple**: `http://51.68.45.123`

Testez depuis votre navigateur !

---

## 🔍 Commandes de dépannage

### Vérifier les logs Streamlit
```bash
sudo journalctl -u streamlit-stat-deces -f
```

### Vérifier les logs Nginx
```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

### Redémarrer les services
```bash
sudo systemctl restart streamlit-stat-deces
sudo systemctl restart nginx
```

### Tester si Streamlit écoute sur le port
```bash
sudo netstat -tlnp | grep 8501
```

### Mettre à jour l'application
```bash
cd ~/stat_deces
git pull origin claude/mortality-trends-tab-hyDoe
sudo systemctl restart streamlit-stat-deces
```

---

## 🔒 ÉTAPE 10 (Optionnel): Ajouter HTTPS avec Let's Encrypt

```bash
# Installer certbot
sudo apt install -y certbot python3-certbot-nginx

# Obtenir un certificat SSL (remplacez par votre domaine)
sudo certbot --nginx -d votre-domaine.com

# Renouvellement automatique
sudo certbot renew --dry-run
```

---

## 📝 Notes importantes

1. **Sécurité**: Changez le mot de passe root après le premier login
2. **Sauvegarde**: Sauvegardez régulièrement `deces.db`
3. **Mémoire**: Surveillez l'utilisation de la RAM avec `htop`
4. **Updates**: Mettez à jour régulièrement le système avec `apt update && apt upgrade`

---

## 🆘 Support

Si vous rencontrez des problèmes:

1. Vérifiez que le service tourne: `sudo systemctl status streamlit-stat-deces`
2. Regardez les logs: `sudo journalctl -u streamlit-stat-deces -n 50`
3. Testez la connexion locale: `curl http://127.0.0.1:8501`
4. Vérifiez le firewall: `sudo ufw status`

---

## ✅ Checklist de déploiement

- [ ] Connexion SSH réussie
- [ ] Python 3, Git, Nginx installés
- [ ] Repository cloné
- [ ] Environnement virtuel créé et packages installés
- [ ] Base de données initialisée
- [ ] Service systemd configuré et actif
- [ ] Nginx configuré et actif
- [ ] Firewall configuré
- [ ] Application accessible depuis l'extérieur
