#!/bin/bash
cd "$(dirname "$0")"
echo "--- H-ITB Elszámolás Indítása (Mac) ---"

if [ ! -f "venv/bin/activate" ]; then
    echo "A hiányzó vagy hibás virtuális környezet törlése és újra létrehozása..."
    rm -rf venv
    python3 -m venv venv
fi

source venv/bin/activate
echo "Függőségek ellenőrzése és telepítése..."
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt

echo "Alkalmazás indítása a böngészőben..."
python3 -m streamlit run app.py
