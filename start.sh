#!/bin/bash
#
# Mortalité France - Lanceur Automatique
# Installation des dépendances et lancement de l'application
#

set -e

# Couleurs
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Configuration
VENV_NAME="venv"
REQUIREMENTS_FILE="requirements.txt"
MAIN_APP="launcher.py"

# Aller dans le répertoire du script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

print_banner() {
    echo -e "${CYAN}"
    echo "╔═══════════════════════════════════════════════════════════════════╗"
    echo "║                                                                   ║"
    echo "║      📊  MORTALITÉ FRANCE - LANCEUR AUTOMATIQUE  📊              ║"
    echo "║                                                                   ║"
    echo "╚═══════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

print_step() {
    echo -e "\n${BLUE}[$1/$2]${NC} ${BOLD}$3${NC}"
    echo "────────────────────────────────────────────────────────────"
}

print_success() {
    echo -e "   ${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "   ${YELLOW}⚠${NC} $1"
}

print_error() {
    echo -e "   ${RED}✗${NC} $1"
}

# Bannière
print_banner

# ============================================================================
# ÉTAPE 1: Vérification de Python
# ============================================================================
print_step 1 4 "Vérification de Python"

# Trouver Python
PYTHON_CMD=""
for cmd in python3 python; do
    if command -v $cmd &> /dev/null; then
        version=$($cmd -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        major=$(echo $version | cut -d. -f1)
        minor=$(echo $version | cut -d. -f2)
        if [ "$major" -ge 3 ] && [ "$minor" -ge 9 ]; then
            PYTHON_CMD=$cmd
            break
        fi
    fi
done

if [ -z "$PYTHON_CMD" ]; then
    print_error "Python 3.9+ n'est pas installé!"
    echo ""
    echo "   Installez Python avec:"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        echo "   brew install python@3.11"
    else
        echo "   sudo apt install python3.11 python3.11-venv python3-pip"
    fi
    echo ""
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version)
print_success "$PYTHON_VERSION détecté"
print_success "Chemin: $(which $PYTHON_CMD)"

# ============================================================================
# ÉTAPE 2: Environnement virtuel
# ============================================================================
print_step 2 4 "Configuration de l'environnement virtuel"

if [ -d "$VENV_NAME" ]; then
    print_success "Environnement virtuel existant trouvé"
else
    echo "   Création de l'environnement virtuel..."
    $PYTHON_CMD -m venv $VENV_NAME
    print_success "Environnement virtuel créé"
fi

# Activer le venv
source "$VENV_NAME/bin/activate"
print_success "Environnement virtuel activé"

# ============================================================================
# ÉTAPE 3: Installation des dépendances
# ============================================================================
print_step 3 4 "Installation des dépendances"

# Mettre à jour pip
echo "   Mise à jour de pip..."
pip install --upgrade pip --quiet

# Installer les requirements
echo "   Installation des packages requis..."
if pip install -r "$REQUIREMENTS_FILE"; then
    print_success "Dépendances installées"
else
    print_error "Erreur lors de l'installation des dépendances"
    exit 1
fi

# Packages optionnels
echo "   Installation des packages optionnels..."
pip install watchdog pyarrow --quiet 2>/dev/null || true
print_success "Packages optionnels traités"

# ============================================================================
# ÉTAPE 4: Vérification
# ============================================================================
print_step 4 4 "Vérification de l'installation"

PACKAGES=("streamlit" "duckdb" "pandas" "plotly" "folium")
ALL_OK=true

for pkg in "${PACKAGES[@]}"; do
    if python -c "import $pkg" 2>/dev/null; then
        version=$(python -c "import $pkg; print($pkg.__version__)" 2>/dev/null || echo "OK")
        echo -e "   ${GREEN}✓${NC} $pkg: $version"
    else
        echo -e "   ${RED}✗${NC} $pkg: NON INSTALLÉ"
        ALL_OK=false
    fi
done

if [ "$ALL_OK" = true ]; then
    print_success "Tous les packages sont installés"
else
    print_warning "Certains packages pourraient manquer"
fi

# ============================================================================
# LANCEMENT
# ============================================================================
echo ""
echo -e "${GREEN}══════════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}   ✓ INSTALLATION TERMINÉE AVEC SUCCÈS!${NC}"
echo -e "${GREEN}══════════════════════════════════════════════════════════════════════${NC}"
echo ""

read -p "Voulez-vous lancer l'application maintenant? [O/n]: " response
response=${response:-O}

if [[ "$response" =~ ^[OoYy]$ ]]; then
    echo ""
    echo "══════════════════════════════════════════════════════════════════════"
    echo "   🚀 DÉMARRAGE DU SERVEUR..."
    echo "   ⏳ Configuration automatique et démarrage..."
    echo "══════════════════════════════════════════════════════════════════════"
    echo ""

    python start.py
else
    echo ""
    echo "   Pour lancer l'application plus tard:"
    echo "   1. source $VENV_NAME/bin/activate"
    echo "   2. python start.py"
    echo ""
fi

echo ""
echo "👋 Au revoir!"
