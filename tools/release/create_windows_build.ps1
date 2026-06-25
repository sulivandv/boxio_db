# Build Windows do Boxio com PyInstaller.
# Execute no PowerShell a partir da raiz do projeto, com o ambiente virtual ativo.

$ErrorActionPreference = "Stop"

python -m pip install -r requirements.txt
python -m pip install pyinstaller

if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
if (Test-Path "dist") { Remove-Item "dist" -Recurse -Force }

pyinstaller `
  --noconfirm `
  --clean `
  --windowed `
  --name "Boxio" `
  --add-data "assets;assets" `
  --add-data "database;database" `
  main.py

$zipPath = "dist\boxio_1.18.0.zip"
Compress-Archive -Path "dist\Boxio\*" -DestinationPath $zipPath -Force
python "tools\release\build_github_release.py" $zipPath "1.18.0"
