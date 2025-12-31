# 🔍 Guide de Diagnostic - Problèmes de Connexion

Ce guide vous aide à diagnostiquer les problèmes d'accès externe à l'application.

## 🚀 Démarrage Rapide

### Étape 1: Lancer le diagnostic

**Windows - Clic droit > Exécuter en tant qu'administrateur:**
```cmd
diagnose.bat
```

**Ou via Python:**
```cmd
python diagnose.py
```

### Étape 2: Analyser les résultats

Le script crée un fichier `diagnostic_YYYYMMDD_HHMMSS.log` avec tous les détails.

## 📋 Tests Effectués

Le script effectue 14 tests complets:

### ✅ Test 1: Informations Système
- OS, version, architecture
- Version Python
- Nom de la machine

### ✅ Test 2: Interfaces Réseau
- Liste complète des interfaces réseau
- Configuration IP de chaque interface

### ✅ Test 3: Détection IP Locale
- Méthode socket (connexion vers 8.8.8.8)
- Méthode hostname
- **IMPORTANT**: Votre IP locale doit correspondre à celle configurée dans la box

### ✅ Test 4: Détection IP Publique
- Test de 4 APIs différentes
- Doit correspondre à l'IP externe de votre box

### ✅ Test 5: Port 8501 - Écoute
- **CRITIQUE**: Vérifie si l'application écoute sur le port 8501
- Test avec netstat
- Test avec socket
- **SI CE TEST ÉCHOUE**: L'application n'est pas lancée!

### ✅ Test 6: Processus Utilisant le Port
- Identifie quel processus utilise le port 8501
- Affiche le PID et le nom du processus
- Devrait montrer Python/Streamlit

### ✅ Test 7: Pare-feu Windows
- **CRITIQUE**: Vérifie les règles de pare-feu pour le port 8501
- Tente de créer une règle si elle n'existe pas
- Affiche l'état du pare-feu

### ✅ Test 8: Connexion Locale
- Test http://localhost:8501
- Test http://127.0.0.1:8501
- **SI CE TEST ÉCHOUE**: L'application a un problème

### ✅ Test 9: Connexion LAN
- Test http://[IP_LOCALE]:8501
- Vérifie l'accès depuis le réseau local

### ✅ Test 10: Configuration Streamlit
- Vérifie le fichier .streamlit/config.toml
- Affiche la configuration (address, port, CORS)

### ✅ Test 11: Résolution DNS
- Teste la connectivité Internet
- Résolution DNS de google.com et 8.8.8.8

### ✅ Test 12: Table de Routage
- Affiche la table de routage complète
- Montre les routes vers Internet

### ✅ Test 13: Ping Passerelle
- Teste la connectivité avec votre box
- Ping vers 192.168.1.254

### ✅ Test 14: Test de Binding
- Vérifie si on peut binder sur 0.0.0.0:8501
- Confirme si l'application est lancée

## 🔧 Problèmes Fréquents et Solutions

### ❌ Problème: "Port 8501 est LIBRE"

**Cause**: L'application n'est pas lancée

**Solution**:
```cmd
python start.py
```
Ou double-cliquez sur `start.bat`

---

### ❌ Problème: "Aucune règle pare-feu pour le port 8501"

**Cause**: Le pare-feu Windows bloque le port

**Solution 1 - Automatique (Admin requis)**:
Le diagnostic tente de créer la règle automatiquement

**Solution 2 - Manuelle**:
```cmd
netsh advfirewall firewall add rule name="Streamlit_8501" dir=in action=allow protocol=TCP localport=8501
```

**Solution 3 - Interface graphique**:
1. Ouvrir "Pare-feu Windows Defender"
2. "Paramètres avancés"
3. "Règles de trafic entrant" > "Nouvelle règle"
4. Type: Port, TCP, 8501
5. Autoriser la connexion

---

### ❌ Problème: "Connexion locale réussie mais pas externe"

**Cause**: Configuration NAT de la box incorrecte

**Solution**:
1. Allez sur http://mabbox.bytel.fr/natpat
2. Vérifiez/créez la règle:
   - Protocole: TCP
   - Port externe: 8501
   - **IP interne**: [Celle trouvée dans Test 3]
   - Port interne: 8501

---

### ❌ Problème: "IP locale différente de 192.168.1.10"

**Cause**: L'IP de votre PC a changé (DHCP)

**Solutions**:
1. Reconfigurez la règle NAT avec la nouvelle IP
2. **OU** Configurez une IP statique sur votre PC:
   - Panneau de configuration > Réseau et Internet
   - Centre réseau et partage
   - Modifier les paramètres de la carte
   - Propriétés > TCP/IPv4
   - Utiliser l'adresse IP suivante: 192.168.1.10

---

### ❌ Problème: "ERR_CONNECTION_TIMED_OUT"

**Causes possibles**:
1. L'application n'est pas lancée (Test 5)
2. Le pare-feu bloque (Test 7)
3. La règle NAT pointe vers la mauvaise IP (Test 3)
4. La box ne fait pas la redirection

**Checklist**:
- [ ] Application lancée sur le PC
- [ ] Accessible en local (http://localhost:8501)
- [ ] Pare-feu autorise le port 8501
- [ ] Règle NAT configurée correctement
- [ ] IP de la règle NAT = IP du PC (Test 3)

---

## 📊 Interpréter le Fichier de Log

Le fichier log contient des timestamps et des niveaux:

```
[   0.00s] [INFO ] Début du diagnostic
[   0.15s] [OK   ] ✅ IP locale (socket): 192.168.1.10
[   2.34s] [ERROR] ❌ Port 8501 est FERMÉ sur localhost
```

**Niveaux**:
- `INFO`: Information générale
- `TEST`: Début d'un test
- `OK`: Test réussi ✅
- `WARN`: Avertissement ⚠️
- `ERROR`: Erreur ❌

## 🆘 Si Rien ne Fonctionne

1. **Exécutez le diagnostic en tant qu'administrateur**
   ```
   Clic droit sur diagnose.bat > Exécuter en tant qu'administrateur
   ```

2. **Lancez l'application**
   ```cmd
   python start.py
   ```

3. **Relancez le diagnostic**
   ```cmd
   python diagnose.py
   ```

4. **Envoyez le fichier de log** `diagnostic_XXXXXXXX_XXXXXX.log`

## 📞 Checklist Finale

Avant de chercher plus loin, vérifiez:

- [ ] Python est installé et fonctionne
- [ ] Les dépendances sont installées (`pip install -r requirements.txt`)
- [ ] L'application est lancée (`python start.py`)
- [ ] Accessible en local: http://localhost:8501 ✅
- [ ] Le pare-feu autorise le port 8501
- [ ] La règle NAT existe dans la box
- [ ] L'IP dans la règle NAT correspond à l'IP du PC (Test 3)
- [ ] L'IP publique de la box est correcte (Test 4)

## 🔬 Diagnostic Avancé

### Test manuel du port

```cmd
# Tester si le port répond localement
curl http://localhost:8501

# Tester depuis le réseau local
curl http://192.168.1.10:8501

# Tester les processus sur le port
netstat -ano | findstr :8501
```

### Tester la redirection NAT depuis l'extérieur

Utilisez un téléphone en 4G (pas en WiFi):
```
http://5.48.33.65:8501
```

Si ça ne marche pas:
1. Le problème est dans la box (NAT)
2. Ou l'IP publique a changé

---

**Bon diagnostic !** 🔍
