@echo off
echo Activating virtual environment...
call venv\Scripts\activate.bat

echo Starting Streamlit app...
streamlit run src\streamlit_app.py

pause
