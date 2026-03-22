@echo off
cd /d "%~dp0"
echo --- H-ITB Elszamolas Inditasa (Windows) ---

IF NOT EXIST venv (
    echo Virtualis kornyezet (/venv/) letrehozasa...
    python -m venv venv
)

echo Virtualis kornyezet aktivalasa...
call venv\Scripts\activate

echo Fuggosegek ellenorzese es telepitese...
pip install -r requirements.txt

echo Alkalmazas inditasa a bongeszoben...
streamlit run app.py
pause
