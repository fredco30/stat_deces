@echo off
chcp 65001 >nul 2>&1
title Mortalité France - Installation et Lancement

echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║                                                                   ║
echo ║      📊  MORTALITÉ FRANCE - LANCEUR AUTOMATIQUE  📊              ║
echo ║                                                                   ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.

:: Aller dans le répertoire du script
cd /d "%~dp0"

:: Vérifier si Python est installé
echo [1/4] Recherche de Python...
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ ERREUR: Python n'est pas installé ou n'est pas dans le PATH!
    echo.
    echo    Veuillez installer Python 3.9+ depuis:
    echo    https://www.python.org/downloads/
    echo.
    echo    ⚠️  Cochez "Add Python to PATH" lors de l'installation!
    echo.
    pause
    exit /b 1
)

:: Afficher la version de Python
for /f "tokens=*" %%i in ('python --version 2^>^&1') do set PYTHON_VERSION=%%i
echo    ✓ %PYTHON_VERSION% détecté

:: Vérifier si l'environnement virtuel existe
echo.
echo [2/4] Vérification de l'environnement virtuel...
if exist "venv\Scripts\activate.bat" (
    echo    ✓ Environnement virtuel trouvé
    echo    Activation du venv...
    call venv\Scripts\activate.bat
) else (
    echo    ⚠ Pas d'environnement virtuel trouvé
    echo    Création du venv...
    python -m venv venv
    if %ERRORLEVEL% NEQ 0 (
        echo    ❌ Erreur lors de la création du venv
        echo    Utilisation de Python système...
        goto :install_deps
    )
    echo    ✓ Environnement virtuel créé
    call venv\Scripts\activate.bat
)

:install_deps
:: Installer/Mettre à jour les dépendances
echo.
echo [3/4] Installation des dépendances...
echo    Mise à jour de pip...
python -m pip install --upgrade pip >nul 2>&1

echo    Installation des packages requis...
python -m pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ ERREUR: L'installation des dépendances a échoué!
    echo    Vérifiez votre connexion internet et réessayez.
    echo.
    pause
    exit /b 1
)

echo    ✓ Dépendances installées

:: Installer les packages optionnels (silencieusement)
echo    Installation des packages optionnels...
python -m pip install watchdog pyarrow >nul 2>&1
echo    ✓ Packages optionnels traités

:: Lancer l'application
echo.
echo [4/4] Lancement de l'application...
echo.
echo ══════════════════════════════════════════════════════════════════════
echo    🚀 DÉMARRAGE DU SERVEUR...
echo    ⏳ Patientez quelques secondes...
echo ══════════════════════════════════════════════════════════════════════
echo.

python launcher.py

:: Si l'application se ferme
echo.
echo ══════════════════════════════════════════════════════════════════════
echo    Application fermée.
echo ══════════════════════════════════════════════════════════════════════
echo.
pause
