<#
.SYNOPSIS
    Checks that Python, Node.js, and Ollama are installed and reports versions.
#>

Write-Host "Experience Intelligence - Dependency Check" -ForegroundColor Cyan
Write-Host "============================================"

function Test-Command($name, $command) {
    try {
        $version = & $command 2>$null
        Write-Host "[OK] $name found: $version" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "[MISSING] $name not found on PATH" -ForegroundColor Red
        return $false
    }
}

$pythonOk = Test-Command "Python" { python --version }
$nodeOk = Test-Command "Node.js" { node --version }
$npmOk = Test-Command "npm" { npm --version }
$ollamaOk = Test-Command "Ollama" { ollama --version }

Write-Host ""
if (-not $pythonOk) {
    Write-Host "Install Python 3.11+ from https://www.python.org/downloads/ (check 'Add to PATH')." -ForegroundColor Yellow
}
if (-not $nodeOk -or -not $npmOk) {
    Write-Host "Install Node.js 18+ from https://nodejs.org/." -ForegroundColor Yellow
}
if (-not $ollamaOk) {
    Write-Host "Install Ollama from https://ollama.com/download - required for local AI extraction." -ForegroundColor Yellow
    Write-Host "Without Ollama, Experience Intelligence still runs: deterministic extraction works," -ForegroundColor Yellow
    Write-Host "but semantic fields, keywords, and AI search summaries will not be generated." -ForegroundColor Yellow
}

if ($pythonOk -and $nodeOk -and $npmOk -and $ollamaOk) {
    Write-Host "All dependencies found. You're ready to run setup-windows.ps1." -ForegroundColor Green
}
