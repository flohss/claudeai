@echo off
setlocal

cd /d "%~dp0"

set PORT=8000

where python >nul 2>nul
if %errorlevel%==0 (
    set "PYCMD=python"
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set "PYCMD=py"
    ) else (
        echo Python est introuvable sur cet ordinateur.
        echo Installez-le depuis https://www.python.org/downloads/ puis relancez ce fichier.
        pause
        exit /b 1
    )
)

echo Demarrage du serveur local sur le port %PORT%...
start "Metro - serveur local" /min cmd /c "%PYCMD% -m http.server %PORT%"

timeout /t 2 /nobreak >nul

start "" "http://localhost:%PORT%/index.html"

echo.
echo Le jeu est ouvert dans votre navigateur.
echo Fermez cette fenetre pour arreter le serveur.
pause >nul

taskkill /fi "WINDOWTITLE eq Metro - serveur local*" /f >nul 2>nul
