# File Converter Application Setup Script for PowerShell
# This script sets up the virtual environment and dependencies

Write-Host "🚀 File Converter Application Setup" -ForegroundColor Green
Write-Host "====================================" -ForegroundColor Green

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ $pythonVersion found" -ForegroundColor Green
} catch {
    Write-Host "❌ Python is not installed or not in PATH" -ForegroundColor Red
    Write-Host "Please install Python 3.8 or higher from https://python.org" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Create virtual environment if it doesn't exist
if (-not (Test-Path "venv")) {
    Write-Host "📦 Creating virtual environment..." -ForegroundColor Cyan
    python -m venv venv
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Failed to create virtual environment" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "✅ Virtual environment created" -ForegroundColor Green
} else {
    Write-Host "📦 Virtual environment already exists" -ForegroundColor Yellow
}

# Activate virtual environment
Write-Host "🔧 Activating virtual environment..." -ForegroundColor Cyan
& ".\venv\Scripts\Activate.ps1"

# Install dependencies
Write-Host "📋 Installing dependencies..." -ForegroundColor Cyan
& ".\venv\Scripts\pip.exe" install -r requirements.txt
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}
Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green

# Create sample data
Write-Host "📊 Creating sample data files..." -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" create_sample_data.py
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: Could not create sample data files" -ForegroundColor Yellow
}

# Run tests
Write-Host "🧪 Running tests..." -ForegroundColor Cyan
& ".\venv\Scripts\python.exe" -m pytest tests/ -v
if ($LASTEXITCODE -ne 0) {
    Write-Host "⚠️  Warning: Some tests failed" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 Setup completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "📖 To start the application:" -ForegroundColor Cyan
Write-Host "1. Activate virtual environment: .\venv\Scripts\Activate.ps1" -ForegroundColor White
Write-Host "2. Run the app: streamlit run src\streamlit_app.py" -ForegroundColor White
Write-Host "3. Open browser: http://localhost:8501" -ForegroundColor White
Write-Host ""
Write-Host "📚 Sample files created:" -ForegroundColor Cyan
Write-Host "   - sample_employees.csv" -ForegroundColor White
Write-Host "   - sample_library.xml" -ForegroundColor White
Write-Host "   - sample_products.csv" -ForegroundColor White
Write-Host ""

# Ask if user wants to start the application immediately
$startApp = Read-Host "Would you like to start the application now? (y/N)"
if ($startApp -eq "y" -or $startApp -eq "Y") {
    Write-Host "🚀 Starting Streamlit application..." -ForegroundColor Green
    & ".\venv\Scripts\streamlit.exe" run src\streamlit_app.py
} else {
    Write-Host "👋 Setup complete. Run the commands above when ready!" -ForegroundColor Green
    Read-Host "Press Enter to exit"
}
