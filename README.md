# 📊 Mortalité France - Tableau de Bord

Application d'analyse statistique des données de décès en France (INSEE).

## 🚀 Démarrage Rapide

### Windows
Double-cliquez sur `start.bat` ou exécutez dans CMD/PowerShell :
```cmd
start.bat
```

### Linux / macOS
```bash
./start.sh
```

### Démarrage manuel avec Python
```bash
python start.py
```

## ✨ Fonctionnalités

- **Import de données INSEE** : Upload et traitement automatique des fichiers CSV
- **Tableau de bord interactif** : Visualisation des statistiques de mortalité
- **Analyses visuelles** : Graphiques, pyramides des âges, heatmaps calendaires
- **Analyse géographique** : Cartes choroplèthes par département
- **Filtres avancés** : Par année, mois, département, sexe
- **Accès distant** : Configuration automatique pour accès depuis l'extérieur

## 🔧 Configuration Réseau (Accès Externe)

### 1. Configuration automatique (recommandé)

Lancez simplement l'application avec `start.bat` ou `start.py`. Le script :
- ✅ Détecte automatiquement votre IP locale
- ✅ Configure Streamlit pour l'accès externe
- ✅ Configure le pare-feu Windows si nécessaire
- ✅ Affiche toutes les URLs d'accès

### 2. Configuration manuelle de votre box internet

Pour un accès depuis Internet, configurez une règle NAT/PAT dans votre box :

```
Protocole : TCP
Port externe : 8501
IP interne : [Votre IP locale - affichée au démarrage]
Port interne : 8501
```

**Exemples d'interfaces box :**
- **Freebox** : http://mafreebox.freebox.fr → Réglages → Redirections de ports
- **Livebox** : http://192.168.1.1 → NAT/PAT
- **SFR Box** : http://192.168.1.1 → Configuration → NAT/PAT
- **Bbox** : http://mabbox.bytel.fr/natpat

### 3. Reconfiguration réseau

Si vous changez de PC ou de réseau WiFi :
```bash
python start.py --reconfigure
```

## 📋 Commandes Disponibles

| Commande | Description |
|----------|-------------|
| `python start.py` | Démarrage avec configuration automatique |
| `python start.py --port 8080` | Démarrage sur un port personnalisé |
| `python start.py --reconfigure` | Forcer la reconfiguration réseau |
| `python setup_network.py` | Configuration réseau uniquement |
| `python launcher.py` | Lancement direct (sans auto-config) |

## 🔑 Authentification

**Mot de passe par défaut :** `mortalite2024`

Pour changer le mot de passe, éditez le fichier `app.py` :
```python
APP_PASSWORD = "votre_nouveau_mot_de_passe"
```

## 📦 Installation Manuelle des Dépendances

Si l'installation automatique échoue :

```bash
pip install -r requirements.txt
```

## 🌐 URLs d'Accès

Après le démarrage, l'application affiche automatiquement :

- **Local** : `http://localhost:8501` (sur votre PC)
- **Réseau local** : `http://192.168.x.x:8501` (même WiFi)
- **Externe** : `http://votre.ip.publique:8501` (depuis Internet, nécessite NAT)

## 📊 Format des Données INSEE

Les fichiers CSV doivent avoir les colonnes suivantes (séparateur `;`) :

- `nomprenom` : Nom et prénom
- `sexe` : 1 (homme) ou 2 (femme)
- `datenaiss` : Date de naissance (YYYYMMDD)
- `lieunaiss` : Lieu de naissance
- `commnaiss` : Commune de naissance
- `paysnaiss` : Pays de naissance
- `datedeces` : Date de décès (YYYYMMDD)
- `lieudeces` : Lieu de décès
- `actedeces` : Acte de décès

## 🛠️ Dépannage

### L'application ne se lance pas
```bash
# Vérifier Python
python --version

# Réinstaller les dépendances
pip install -r requirements.txt --force-reinstall
```

### Pas d'accès depuis l'extérieur
1. Vérifiez que l'application est lancée : `http://localhost:8501`
2. Vérifiez le pare-feu Windows
3. Vérifiez la configuration NAT de votre box
4. Relancez la configuration : `python start.py --reconfigure`

### Le port 8501 est déjà utilisé
```bash
python start.py --port 8080
```

### Diagnostic réseau
Le fichier `network_info.txt` (créé au démarrage) contient :
- Votre IP locale actuelle
- Votre IP publique
- La configuration NAT recommandée

## 📁 Structure du Projet

```
stat_deces/
├── app.py                  # Application Streamlit principale
├── launcher.py             # Lanceur avec détection IP
├── start.py                # Script de démarrage automatique
├── setup_network.py        # Configuration réseau automatique
├── etl_utils.py            # Utilitaires ETL et base de données
├── requirements.txt        # Dépendances Python
├── start.bat               # Lanceur Windows
├── start.sh                # Lanceur Linux/macOS
├── .streamlit/
│   └── config.toml         # Configuration Streamlit (auto-généré)
└── network_info.txt        # Infos réseau (auto-généré)
```

## 🔒 Sécurité

**⚠️ IMPORTANT** : Cette application est conçue pour un usage personnel ou en réseau de confiance.

Pour un déploiement en production :
1. Changez le mot de passe par défaut
2. Utilisez HTTPS (certificat SSL/TLS)
3. Configurez une authentification robuste
4. Limitez l'accès par IP si possible

## 📄 Licence

Projet personnel - Analyse des données publiques INSEE

## 🆘 Support

Pour tout problème :
1. Consultez `network_info.txt` pour les informations réseau
2. Vérifiez les logs de l'application
3. Relancez avec `python start.py --reconfigure`

---

**Développé avec** : Python, Streamlit, DuckDB, Plotly, Folium
