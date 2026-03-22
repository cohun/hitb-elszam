#!/bin/bash
cd "$(dirname "$0")"
echo "--- H-ITB Elszámolás Indítása (Mac) ---"

if [ ! -d "venv" ]; then
    echo "Virtuális környezet (/venv/) létrehozása..."
    python3 -m venv venv
fi

source venv/bin/activate
echo "Függőségek ellenőrzése és telepítése..."
pip install -r requirements.txt

echo "Alkalmazás indítása a böngészőben..."
streamlit run app.py
