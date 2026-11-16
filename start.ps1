param([int]$Port = 8501)
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path -LiteralPath '.\.venv\Scripts\python.exe')) { throw 'Run .\install.ps1 first.' }
& .\.venv\Scripts\python.exe -m streamlit run dashboard.py --server.address localhost --server.port $Port --browser.gatherUsageStats false
if ($LASTEXITCODE -ne 0) { throw 'App startup failed.' }
