<#
.SYNOPSIS
    Pulls the local LLM model used by Experience Intelligence via Ollama.
.PARAMETER Model
    The Ollama model name to pull. Defaults to the value in backend/.env (OLLAMA_MODEL)
    or "llama3.1" if not set.
#>
param(
    [string]$Model = ""
)

if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
    Write-Host "Ollama is not installed. Download it from https://ollama.com/download first." -ForegroundColor Red
    exit 1
}

if (-not $Model) {
    $envFile = Join-Path $PSScriptRoot "..\backend\.env"
    $Model = "llama3.1"
    if (Test-Path $envFile) {
        $line = Get-Content $envFile | Where-Object { $_ -match "^OLLAMA_MODEL=" }
        if ($line) {
            $Model = ($line -split "=", 2)[1].Trim()
        }
    }
}

Write-Host "Pulling Ollama model: $Model" -ForegroundColor Cyan
ollama pull $Model

Write-Host ""
Write-Host "Starting Ollama server (if not already running)..." -ForegroundColor Cyan
Start-Process -NoNewWindow -FilePath "ollama" -ArgumentList "serve" -ErrorAction SilentlyContinue

Write-Host "Verifying model is available..." -ForegroundColor Cyan
ollama list

Write-Host ""
Write-Host "Done. Experience Intelligence will use OLLAMA_BASE_URL=http://localhost:11434 and OLLAMA_MODEL=$Model" -ForegroundColor Green
