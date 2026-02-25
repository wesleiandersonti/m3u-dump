$ErrorActionPreference = 'Stop'

python -m pip install --upgrade pip
pip install .
pip install pyinstaller

pyinstaller --noconfirm --onefile --windowed --name m3u-dump-pro m3u_dump\gui.py

Write-Host "Build finalizado: dist\m3u-dump-pro.exe"
