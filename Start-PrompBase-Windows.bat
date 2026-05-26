@echo off
setlocal
title PrompBase Python
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
echo Pobierz: https://www.python.org/downloads/
pause

:end
endlocal
