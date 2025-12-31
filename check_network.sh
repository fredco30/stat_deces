#!/bin/bash
# Script de diagnostic réseau pour l'application Mortalité France

echo "========================================"
echo "  DIAGNOSTIC RÉSEAU - MORTALITÉ FRANCE"
echo "========================================"
echo ""

# 1. Adresse IP locale
echo "📍 Adresse IP locale:"
LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || ip addr show | grep 'inet ' | grep -v '127.0.0.1' | head -1 | awk '{print $2}' | cut -d/ -f1)
echo "   → $LOCAL_IP"
echo ""

# 2. Port 8501
echo "🔌 Port 8501:"
if ss -tlnp 2>/dev/null | grep -q ":8501 " || netstat -tlnp 2>/dev/null | grep -q ":8501 "; then
    echo "   ✅ Processus actif sur le port 8501"
    ss -tlnp 2>/dev/null | grep ":8501 " || netstat -tlnp 2>/dev/null | grep ":8501 "
else
    echo "   ❌ Aucun processus sur le port 8501"
    echo "   → Lancez l'application avec: python launcher.py"
fi
echo ""

# 3. Firewall
echo "🔥 Firewall (ufw):"
if command -v ufw &> /dev/null; then
    UFW_STATUS=$(ufw status 2>/dev/null | grep -i "status" | awk '{print $2}')
    if [ "$UFW_STATUS" = "active" ]; then
        echo "   ⚠️  UFW actif - vérifiez les règles:"
        ufw status | grep 8501
        if ! ufw status | grep -q 8501; then
            echo "   ❌ Port 8501 non autorisé"
            echo "   → Ajoutez: sudo ufw allow 8501/tcp"
        fi
    else
        echo "   ✅ UFW inactif"
    fi
else
    echo "   ℹ️  UFW non installé"
fi
echo ""

# 4. Configuration Streamlit
echo "⚙️  Configuration Streamlit:"
if [ -f ".streamlit/config.toml" ]; then
    echo "   ✅ Fichier config.toml présent"
    echo "   Contenu:"
    cat .streamlit/config.toml | grep -E "address|port|enableCORS"
else
    echo "   ❌ Fichier config.toml manquant"
fi
echo ""

# 5. NAT Configuration recommandée
echo "🌐 Configuration NAT recommandée pour votre box:"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   Protocole:    TCP"
echo "   Port externe: 8501"
echo "   IP interne:   $LOCAL_IP"
echo "   Port interne: 8501"
echo "   ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# 6. Test de connectivité
echo "🧪 Test d'accès local:"
if curl -s -o /dev/null -w "%{http_code}" http://localhost:8501 2>/dev/null | grep -q "200\|302"; then
    echo "   ✅ Application accessible localement"
else
    echo "   ❌ Application non accessible"
    echo "   → Vérifiez que l'application est lancée"
fi
echo ""

echo "========================================"
echo "  INSTRUCTIONS DE CORRECTION"
echo "========================================"
echo ""
echo "1. Mettez à jour la règle NAT 'stat_mortalité' dans votre box:"
echo "   - IP interne: $LOCAL_IP (au lieu de 192.168.1.10)"
echo ""
echo "2. Si le firewall bloque le port 8501:"
echo "   sudo ufw allow 8501/tcp"
echo ""
echo "3. Lancez l'application si elle n'est pas démarrée:"
echo "   python launcher.py"
echo ""
echo "4. Testez l'accès externe avec:"
echo "   http://5.48.33.65:8501"
echo ""
