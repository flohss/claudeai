@echo off
cd /d "%~dp0"
set PORT=8934

where python >nul 2>nul
if %errorlevel%==0 (
    set PYCMD=python
) else (
    where py >nul 2>nul
    if %errorlevel%==0 (
        set PYCMD=py
    ) else (
        echo Python est necessaire mais n'a pas ete trouve sur cet ordinateur.
        echo Installez-le depuis https://www.python.org/downloads/
        echo ^(cochez bien la case "Add python.exe to PATH" pendant l'installation^)
        echo puis relancez ce fichier.
        pause
        exit /b 1
    )
)

echo Demarrage du serveur local sur http://localhost:%PORT%/ ...
start "Vortex Infini - serveur (ne pas fermer)" /min cmd /c "%PYCMD% -m http.server %PORT%"

timeout /t 1 /nobreak >nul
start "" "http://localhost:%PORT%/"

echo.
echo Le jeu devrait s'ouvrir dans votre navigateur.
echo Pour arreter le serveur, fermez la fenetre "Vortex Infini - serveur".
echo Vous pouvez fermer cette fenetre-ci.
pause
