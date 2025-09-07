#!/usr/bin/env python3
"""
Setup script for the File Converter application.
This script sets up the virtual environment and installs dependencies.
"""

import os
import subprocess
import sys
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors."""
    print(f"📋 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed:")
        print(f"   Error: {e.stderr}")
        return False


def main():
    """Main setup function."""
    print("🚀 Setting up File Converter Application")
    print("=" * 50)
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("❌ Python 3.8 or higher is required")
        sys.exit(1)
    
    print(f"✅ Python {sys.version.split()[0]} detected")
    
    # Get the project directory
    project_dir = Path(__file__).parent
    os.chdir(project_dir)
    
    print(f"📁 Working directory: {project_dir}")
    
    # Create virtual environment
    venv_path = project_dir / "venv"
    
    if venv_path.exists():
        print("📦 Virtual environment already exists")
    else:
        if not run_command("python -m venv venv", "Creating virtual environment"):
            sys.exit(1)
    
    # Determine activation script based on OS
    if os.name == 'nt':  # Windows
        activate_script = venv_path / "Scripts" / "activate.bat"
        pip_executable = venv_path / "Scripts" / "pip.exe"
        python_executable = venv_path / "Scripts" / "python.exe"
    else:  # Unix/Linux/MacOS
        activate_script = venv_path / "bin" / "activate"
        pip_executable = venv_path / "bin" / "pip"
        python_executable = venv_path / "bin" / "python"
    
    # Install dependencies
    install_cmd = f'"{pip_executable}" install -r requirements.txt'
    if not run_command(install_cmd, "Installing dependencies"):
        sys.exit(1)
    
    # Create sample data
    sample_cmd = f'"{python_executable}" create_sample_data.py'
    if not run_command(sample_cmd, "Creating sample data files"):
        print("⚠️  Warning: Could not create sample data files")
    
    # Run tests
    test_cmd = f'"{python_executable}" -m pytest tests/ -v'
    if not run_command(test_cmd, "Running tests"):
        print("⚠️  Warning: Some tests failed")
    
    print("\n🎉 Setup completed successfully!")
    print("\n📖 Next steps:")
    print("1. Activate the virtual environment:")
    
    if os.name == 'nt':  # Windows
        print("   .\\venv\\Scripts\\Activate.ps1    (PowerShell)")
        print("   .\\venv\\Scripts\\activate.bat    (Command Prompt)")
    else:
        print("   source venv/bin/activate")
    
    print("\n2. Start the application:")
    print("   streamlit run src/streamlit_app.py")
    
    print("\n3. Open your browser to:")
    print("   http://localhost:8501")
    
    print("\n📚 Sample files created:")
    print("   - sample_employees.csv")
    print("   - sample_library.xml")
    print("   - sample_products.csv")


if __name__ == "__main__":
    main()
