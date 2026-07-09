@echo off
setlocal

cd /d "%~dp0"

uv run pyinstaller ^
  --noconfirm ^
  --clean ^
  --onefile ^
  --name ncdl ^
  --specpath build ^
  --paths "%~dp0src" ^
  --add-data "%~dp0src\ui\css\ui.css;ui\css" ^
  "%~dp0src\main.py"
