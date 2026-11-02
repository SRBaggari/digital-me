<#
.SYNOPSIS
  Start Digital Me locally and open it in the browser.
.EXAMPLE
  .\start.ps1 -Instance alice
  .\start.ps1 -Instance alice -Rebuild   # rebuild the UI after changing frontend code
#>
param(
    [string]$Instance,
    [switch]$Rebuild,
    [int]$Port = 0
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot

foreach ($tool in "uv", "npm", "ollama") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        Write-Error "'$tool' is not installed. See README.md > Setup."
    }
}

if ($Rebuild -or -not (Test-Path "$root\frontend\dist\index.html")) {
    Write-Host "Building the interface..." -ForegroundColor Cyan
    Push-Location "$root\frontend"
    try {
        if (-not (Test-Path node_modules)) { npm ci }
        npm run build
        if ($LASTEXITCODE -ne 0) { throw "Frontend build failed" }
    } finally { Pop-Location }
}

$serveArgs = @("run", "digital-me", "serve")
if ($Instance) { $serveArgs += @("--instance", $Instance) }
if ($Port) { $serveArgs += @("--port", $Port) }
$url = if ($Port) { "http://127.0.0.1:$Port" } else { "http://127.0.0.1:8765" }

# Open the browser once the server answers.
Start-Job -ArgumentList $url -ScriptBlock {
    param($url)
    for ($i = 0; $i -lt 60; $i++) {
        try { Invoke-WebRequest "$url/api/status" -UseBasicParsing -TimeoutSec 1 | Out-Null; Start-Process $url; return }
        catch { Start-Sleep -Milliseconds 500 }
    }
} | Out-Null

Push-Location "$root\backend"
try { uv @serveArgs } finally { Pop-Location }
