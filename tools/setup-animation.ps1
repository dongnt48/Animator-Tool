$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
Push-Location $projectRoot
try {
    # Stable speech dependencies have wheels for Python 3.13.
    py install -y 3.13
    if ($LASTEXITCODE -ne 0) { throw 'Cannot install Python 3.13.' }
    py -3.13 -m venv .venv-speech
    if ($LASTEXITCODE -ne 0) { throw 'Cannot create speech environment.' }
    & .\.venv-speech\Scripts\python.exe -m pip install -r requirements-animation.txt
    if ($LASTEXITCODE -ne 0) { throw 'Cannot install speech dependencies.' }
    Push-Location remotion
    try {
        npm.cmd ci
        if ($LASTEXITCODE -ne 0) { throw 'Cannot install Remotion dependencies.' }
    } finally { Pop-Location }
    Write-Host 'Speech and Remotion ready. Install the official agy CLI if missing:'
    Write-Host 'https://antigravity.google/docs/getting-started?tab=cli'
    Write-Host 'Then run agy in your terminal and sign in with your Google account.'
} finally { Pop-Location }
