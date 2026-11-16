param([string]$PythonVersion = "3.11")
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw 'Install 64-bit Python 3.11 from python.org with the Python launcher, then rerun.'
}
& py "-$PythonVersion" -m venv .venv
if ($LASTEXITCODE -ne 0) { throw "Python $PythonVersion not found. Install it, or run .\install.ps1 -PythonVersion 3.9 for the tested compatibility runtime." }
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
if ($LASTEXITCODE -ne 0) { throw 'pip upgrade failed. Check internet access.' }
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed. Check internet access.' }
& .\.venv\Scripts\python.exe -m pytest -v
if ($LASTEXITCODE -ne 0) { throw 'Tests failed; inspect the output before launching.' }
Write-Host 'Ready. Run .\start.ps1'
