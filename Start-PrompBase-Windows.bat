@echo off
setlocal
title PrompBase 2.5
cd /d "%~dp0"

where py >nul 2>nul
if %errorlevel%==0 (
  py -3 "%~dp0promptbase.py"
  goto :end
)

where python >nul 2>nul
if %errorlevel%==0 (
  python "%~dp0promptbase.py"
  goto :end
)

echo Python 3 nie zostal znaleziony.
echo.
echo Uzytkownik Windows bez Pythona:
echo Pobierz PrompBase.exe z GitHub Releases
echo https://github.com/zetmar-collab/PrompBase-Python/releases
echo.
pause

:end
endlocal
