@echo off
title PrompBase - strona produktu
cd /d "%~dp0"
if exist "landing\index.html" (
  start "" "%~dp0landing\index.html"
) else (
  echo Brak pliku landing\index.html
  start "" "https://github.com/zetmar-collab/PrompBase-Python/releases"
)
exit /b 0
