$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
& .\.venv\Scripts\python.exe -m pytest -v --junitxml=test-results.xml
if ($LASTEXITCODE -ne 0) { throw 'Tests failed.' }
