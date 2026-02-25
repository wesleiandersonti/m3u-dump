@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Instalando dependencias de build...
python -m pip install --user --upgrade pip
python -m pip install --user pyinstaller

if errorlevel 1 (
  echo [ERRO] Falha ao instalar PyInstaller.
  pause
  exit /b 1
)

echo [2/4] Instalando pacote local...
python -m pip install --user .

if errorlevel 1 (
  echo [ERRO] Falha ao instalar o pacote local.
  pause
  exit /b 1
)

echo [3/4] Gerando EXE...
python -m PyInstaller --noconfirm --onefile --windowed --name m3u-dump-pro m3u_dump\gui.py

if errorlevel 1 (
  echo [ERRO] Falha ao gerar EXE.
  pause
  exit /b 1
)

echo [4/4] Gerando instalador Inno Setup...
set "ISCC1=C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
set "ISCC2=C:\Program Files\Inno Setup 6\ISCC.exe"

if exist "%ISCC1%" (
  "%ISCC1%" installer\m3u-dump-pro.iss
) else if exist "%ISCC2%" (
  "%ISCC2%" installer\m3u-dump-pro.iss
) else (
  echo [ERRO] Inno Setup nao encontrado.
  echo Instale: https://jrsoftware.org/isinfo.php
  pause
  exit /b 1
)

echo =========================================
echo Pronto!
echo EXE: dist\m3u-dump-pro.exe
echo Instalador: installer\m3u-dump-pro-installer.exe
echo =========================================
pause
endlocal
