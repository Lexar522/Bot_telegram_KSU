# PowerShell launcher for Telegram bot (English output to avoid mojibake)
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "Telegram Bot - KSU"

Clear-Host
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "          TELEGRAM BOT - KHERSON STATE UNIVERSITY (KSU)" -ForegroundColor Green
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host ""

# Configure local models path for Ollama inside project
$projectRoot = Get-Location
$ollamaModelsPath = Join-Path $projectRoot "ollama_models"
if (-not (Test-Path $ollamaModelsPath)) {
    New-Item -ItemType Directory -Path $ollamaModelsPath | Out-Null
}
$env:OLLAMA_MODELS = $ollamaModelsPath
Write-Host "[INFO] OLLAMA_MODELS set to: $ollamaModelsPath" -ForegroundColor Cyan

# Check Python
Write-Host "[INFO] Checking Python..." -ForegroundColor Cyan
try {
    $pythonVersion = python --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "Python not found" }
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Python not found! Install Python 3.8+" -ForegroundColor Red
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Ensure virtual environment exists
if (-not (Test-Path "venv")) {
    Write-Host "[WARN] Virtual environment not found. Creating..." -ForegroundColor Yellow
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[OK] Virtual environment created" -ForegroundColor Green
    Write-Host ""
}

# Activate virtual environment
Write-Host "[INFO] Activating virtual environment..." -ForegroundColor Cyan
& "venv\Scripts\Activate.ps1"
if ($LASTEXITCODE -ne 0) {
    Write-Host "[ERROR] Failed to activate virtual environment" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Ensure we use venv Python
$pythonPath = (Get-Command python).Source
Write-Host "[INFO] Current python: $pythonPath" -ForegroundColor Cyan
if (-not $pythonPath.Contains("venv")) {
    Write-Host "[WARN] System python detected, switching to venv python..." -ForegroundColor Yellow
    $pythonPath = Join-Path (Get-Location) "venv\Scripts\python.exe"
    if (Test-Path $pythonPath) {
        $env:Path = "$(Join-Path (Get-Location) 'venv\Scripts');$env:Path"
        Write-Host "[OK] Using venv python: $pythonPath" -ForegroundColor Green
    } else {
        Write-Host "[ERROR] venv python not found!" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Install dependencies if missing
if (-not (Test-Path "venv\Lib\site-packages\aiogram")) {
    Write-Host "[WARN] Dependencies not installed. Installing..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to install dependencies" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "[OK] Dependencies installed" -ForegroundColor Green
    Write-Host ""
}

# Ensure Ollama model is available locally (within project models path)
$ollamaModelName = "llama3.1:8b"
Write-Host "[INFO] Checking Ollama model ($ollamaModelName)..." -ForegroundColor Cyan
$modelExists = $false
try {
    $modelExists = $null -ne (ollama list 2>$null | Select-String -SimpleMatch $ollamaModelName)
} catch {}
if (-not $modelExists) {
    Write-Host "[WARN] Model not found locally. Pulling $ollamaModelName into $ollamaModelsPath ..." -ForegroundColor Yellow
    ollama pull $ollamaModelName
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[ERROR] Failed to pull model $ollamaModelName. Start Ollama (ollama serve) and check internet." -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
}

# Optional: start Ollama if not running (best-effort)
Write-Host "[INFO] Ensuring Ollama is running (best-effort)..." -ForegroundColor Cyan
try {
    $null = Invoke-WebRequest -UseBasicParsing -Uri "http://localhost:11434/api/tags" -TimeoutSec 2
} catch {
    # Try to start Ollama serve
    try {
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 3
    } catch {
        Write-Host "[WARN] Could not auto-start Ollama. Start it manually with 'ollama serve'." -ForegroundColor Yellow
    }
}

# Check .env presence
if (-not (Test-Path ".env")) {
    Write-Host "[WARN] .env file not found!" -ForegroundColor Yellow
    Write-Host "[INFO] Create .env with:" -ForegroundColor Cyan
    Write-Host "     BOT_TOKEN=your_bot_token_here"
    Write-Host "     OLLAMA_API_URL=http://localhost:11434"
    Write-Host "     ADMIN_ID=your_admin_id"
    Write-Host "     DB_HOST=localhost"
    Write-Host "     DB_PORT=5432"
    Write-Host "     DB_NAME=admission_bot"
    Write-Host "     DB_USER=postgres"
    Write-Host "     DB_PASSWORD=your_password"
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Stop previous python processes (optional)
Write-Host "[INFO] Checking running python processes..." -ForegroundColor Cyan
$pythonProcesses = Get-Process -Name python -ErrorAction SilentlyContinue
if ($pythonProcesses) {
    Write-Host "[WARN] Found running python processes. Stopping them..." -ForegroundColor Yellow
    Stop-Process -Name python -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2
    Write-Host "[OK] Previous processes stopped" -ForegroundColor Green
    Write-Host ""
}

# Main start
Write-Host "================================================================" -ForegroundColor Green
Write-Host "                    STARTING BOT..." -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "[INFO] Details:" -ForegroundColor Cyan
Write-Host "     - Python: $pythonVersion"
Write-Host "     - Workdir: " (Get-Location)
Write-Host "     - Start time: " (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
Write-Host ""
Write-Host "[HINT] Press Ctrl+C to stop the bot" -ForegroundColor Yellow
Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""

# Determine python path for run
if (Test-Path "venv\Scripts\python.exe") {
    $pythonExe = "venv\Scripts\python.exe"
} else {
    $pythonExe = "python"
}

Write-Host "[INFO] Using: $pythonExe" -ForegroundColor Cyan
Write-Host ""
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host "BOT LOGS:" -ForegroundColor Gray
Write-Host "----------------------------------------" -ForegroundColor Gray
Write-Host ""

# Run bot unbuffered
& $pythonExe -u main.py
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Write-Host ""
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host "                    BOT START ERROR" -ForegroundColor Red
    Write-Host "================================================================" -ForegroundColor Red
    Write-Host ""
    Write-Host "[INFO] Exit code: $exitCode" -ForegroundColor Red
    Write-Host ""
    Write-Host "[INFO] Possible reasons:" -ForegroundColor Cyan
    Write-Host "     - Wrong BOT_TOKEN in .env"
    Write-Host "     - OLLAMA is not running"
    Write-Host "     - Database connection issues"
    Write-Host "     - Missing dependencies"
    Write-Host "     - Code error"
    Write-Host ""
    Write-Host "[HINT] Check logs above for details" -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

# Normal finish
Write-Host ""
Write-Host "[INFO] Bot stopped" -ForegroundColor Yellow
Read-Host "Press Enter to exit"
