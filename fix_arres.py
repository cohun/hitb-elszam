import sqlite3
import pandas as pd
import numpy as np

KIMENO_PATH = 'Excels/Kimenő számlák.xls'
ELABE_PATH = 'Excels/Elabe_lista.xls'
DB_PATH = 'hitb_database.db'

print("Excels betöltése (xlrd szükséges)...")
df_kimen = pd.read_excel(KIMENO_PATH, engine='xlrd')
df_elabe = pd.read_excel(ELABE_PATH, engine='xlrd')

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

cursor.execute("SELECT Szla, Cikk, Darab, Elad, SzumElad FROM forgalom")
rows = cursor.fetchall()

updates = []

for szla, cikk, darab_db, elad_db, szum_elad_db in rows:
    szla_str = str(szla)
    cikk_str = str(cikk)
    
    erows = df_elabe[(df_elabe['Bizonylatszám'].astype(str) == szla_str) & 
                     (df_elabe['Cikkszám'].astype(str) == cikk_str)]
                     
    szum_beker = 0.0
    beker_ar = 0.0
    
    # Kiszámoljuk az elábé listából tételenként (Mennyiség * Bekerár)
    if not erows.empty:
        szum_beker_temp = 0.0
        sum_darab_elabe = 0.0
        for _, erow in erows.iterrows():
            e_menny = pd.to_numeric(erow.get('Mennyiség', 0), errors='coerce')
            if pd.isnull(e_menny): e_menny = 0.0
            
            e_beker = pd.to_numeric(erow.get('Bekerár', 0), errors='coerce')
            if pd.isnull(e_beker) or e_beker == 0.0:
                e_beker = pd.to_numeric(erow.get('Átlag bekerár', erow.get('Egységár', 0)), errors='coerce')
            if pd.isnull(e_beker): e_beker = 0.0
                
            szum_beker_temp += (e_menny * e_beker)
            sum_darab_elabe += e_menny
            
        if szum_beker_temp > 0:
            szum_beker = szum_beker_temp
            beker_ar = szum_beker / sum_darab_elabe if sum_darab_elabe > 0 else 0.0
            
    # Fallback, ha az Elábé üres lenne vagy 0-t hozna
    if szum_beker == 0.0:
        krows = df_kimen[(df_kimen['Számla száma'].astype(str) == szla_str) & 
                         (df_kimen['Cikkszám'].astype(str) == cikk_str)]
        if not krows.empty:
            darab_kimen = pd.to_numeric(krows.iloc[0].get('Mennyiség', 0), errors='coerce')
            if pd.isnull(darab_kimen): darab_kimen = 0.0
            beker_kimen = pd.to_numeric(krows.iloc[0].get('Átlag bekerár', 0), errors='coerce')
            if pd.isnull(beker_kimen): beker_kimen = 0.0
            
            szum_beker = darab_kimen * beker_kimen
            beker_ar = beker_kimen
            
    szum_elad = szum_elad_db if szum_elad_db is not None else 0.0
    
    # A felhasználó excel logikája: IF([@SzumElad]<0;[@SzumElad]-[@SzumBeker]*-1;[@SzumElad]-[@SzumBeker])
    if szum_elad < 0:
        res = szum_elad - (szum_beker * -1)
    else:
        res = szum_elad - szum_beker
    
    updates.append((float(beker_ar), float(szum_beker), float(res), szla_str, cikk_str))

print(f"{len(updates)} rekord frissítése az adatbázisban...")
cursor.executemany('''
    UPDATE forgalom
    SET Beker = ?, SzumBeker = ?, Rés = ?
    WHERE Szla = ? AND Cikk = ?
''', updates)

conn.commit()
conn.close()

print("Sikeres javítás!")
