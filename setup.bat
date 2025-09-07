@echo off
echo 🚀 File Converter Application Setup
echo ====================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python 3.8 or higher from https://python.org
    pause
    exit /b 1
)

echo ✅ Python found

REM Create virtual environment if it doesn't exist
if not exist "venv" (
    echo 📦 Creating virtual environment...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ❌ Failed to create virtual environment
        pause
        exit /b 1
    )
    echo ✅ Virtual environment created
) else (
    echo 📦 Virtual environment already exists
)

REM Activate virtual environment and install dependencies
echo 📋 Installing dependencies...
call venv\Scripts\activate.bat
pip install -r requirements.txt
if %errorlevel% neq 0 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Dependencies installed successfully

REM Create sample data
echo 📊 Creating sample data files...
python create_sample_data.py
if %errorlevel% neq 0 (
    echo ⚠️  Warning: Could not create sample data files
)

REM Run tests
echo 🧪 Running tests...
python -m pytest tests/ -v
if %errorlevel% neq 0 (
    echo ⚠️  Warning: Some tests failed
)

echo.
echo 🎉 Setup completed successfully!
echo.
echo 📖 To start the application:
echo 1. Activate virtual environment: venv\Scripts\activate.bat
echo 2. Run the app: streamlit run src\streamlit_app.py
echo 3. Open browser: http://localhost:8501
echo.
echo 📚 Sample files created:
echo    - sample_employees.csv
echo    - sample_library.xml
echo    - sample_products.csv
echo.
pause
