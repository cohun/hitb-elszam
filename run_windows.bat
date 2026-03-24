@echo off
cd /d "%~dp0"
echo --- H-ITB Elszamolas Inditasa (Windows) ---

IF NOT EXIST "venv\Scripts\activate.bat" (
    echo A hianyzo vagy hibas virtualis kornyezet torlese es ujra letrehozasa...
    rmdir /s /q venv 2>nul
    python -m venv venv
)

echo Virtualis kornyezet aktivalasa...
call venv\Scripts\activate.bat

echo Fuggosegek ellenorzese es telepitese...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo Alkalmazas inditasa a bongeszoben...
python -m streamlit run app.py
pause
