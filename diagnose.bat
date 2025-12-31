@echo off
chcp 65001 >nul 2>&1
title Diagnostic Réseau - Mortalité France

echo.
echo ╔═══════════════════════════════════════════════════════════════════╗
echo ║                                                                   ║
echo ║         🔍  DIAGNOSTIC RÉSEAU ULTRA-DÉTAILLÉ  🔍                 ║
echo ║                                                                   ║
echo ║              Application Mortalité France                        ║
echo ║                                                                   ║
echo ╚═══════════════════════════════════════════════════════════════════╝
echo.
echo.
echo ⚠️  IMPORTANT: Pour un diagnostic complet, exécutez en tant qu'ADMINISTRATEUR
echo    (Clic droit sur le fichier ^> Exécuter en tant qu'administrateur)
echo.
echo    Sinon, certaines règles de pare-feu ne pourront pas être créées.
echo.
pause
echo.

:: Aller dans le répertoire du script
cd /d "%~dp0"

:: Vérifier si Python est installé
where python >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo ❌ ERREUR: Python n'est pas installé ou n'est pas dans le PATH!
    echo.
    pause
    exit /b 1
)

echo ══════════════════════════════════════════════════════════════════════
echo    Lancement du diagnostic...
echo ══════════════════════════════════════════════════════════════════════
echo.

:: Lancer le script de diagnostic
python diagnose.py

echo.
echo ══════════════════════════════════════════════════════════════════════
echo    Diagnostic terminé
echo ══════════════════════════════════════════════════════════════════════
echo.
echo Le fichier de log a été créé dans le dossier avec tous les détails.
echo.
pause
