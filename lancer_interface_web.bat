@echo off
setlocal

cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python n'a pas ete trouve dans le PATH.
    echo Installez-le depuis https://www.python.org/downloads/ puis reessayez.
    echo ^(pensez a cocher "Add python.exe to PATH" pendant l'installation^)
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo Premiere fois : creation de l'environnement virtuel...
    python -m venv .venv
    if errorlevel 1 (
        echo La creation de l'environnement virtuel a echoue.
        pause
        exit /b 1
    )
)

echo Installation des dependances de l'interface graphique ^(si necessaire^)...
".venv\Scripts\python.exe" -m pip install -r requirements-web.txt --quiet
if errorlevel 1 (
    echo.
    echo L'installation des dependances a echoue. Verifiez votre connexion internet.
    pause
    exit /b 1
)

echo.
echo Lancement de l'interface graphique...
echo Le navigateur va s'ouvrir sur http://localhost:5000 dans quelques secondes.
echo ^(Fermez cette fenetre pour arreter le serveur.^)
echo.

start "" cmd /c "timeout /t 2 >nul && start http://localhost:5000"
".venv\Scripts\python.exe" -m webapp.app

pause
