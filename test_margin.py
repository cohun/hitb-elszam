import sqlite3
import pandas as pd
import numpy as np

# Let's get the original data from kimen to see what exact formula the user used.
kimen = pd.read_excel('Excels/Kimenő számlák.xls', engine='xlrd')
elabe = pd.read_excel('Excels/Elabe_lista.xls', engine='xlrd')

# How did the user calculate it? "Az excelben így kezeltem =IF([@SzumElad]<0;[@SzumElad]-[@SzumBeker]*-1;[@SzumElad]-[@SzumBeker])"
# What is SzumBeker in the user's Excel?
# "A SzumBeker az Elaba_lista.xls fájlból kell számolni és ennek értéke tételenként Mennyiség * Bekarár."

# Let's manually loop over all kimen invoices and do the exact match.
alap_1 = 0
for idx, row in kimen.iterrows():
    szla = str(row.get('Számla száma'))
    cikk = str(row.get('Cikkszám'))
    datum = pd.to_datetime(row.get('Dátum'), errors='coerce')
    if pd.isnull(datum): continue
    if datum.month != 1: continue
    
    darab_kimen = pd.to_numeric(row.get('Mennyiség', 0), errors='coerce')
    elad = pd.to_numeric(row.get('Egységár', 0), errors='coerce')
    szum_elad = darab_kimen * elad
    if pd.isnull(szum_elad): szum_elad = 0.0

    erows = elabe[(elabe['Bizonylatszám'].astype(str) == szla) & (elabe['Cikkszám'].astype(str) == cikk)]
    szum_beker = 0.0
    for _, erow in erows.iterrows():
        e_menny = pd.to_numeric(erow.get('Mennyiség', 0), errors='coerce')
        e_beker = pd.to_numeric(erow.get('Bekerár', 0), errors='coerce')
        if pd.notnull(e_menny) and pd.notnull(e_beker):
            szum_beker += e_menny * e_beker
            
    # Fallback?
    if szum_beker == 0.0:
        beker_kimen = pd.to_numeric(row.get('Átlag bekerár', 0), errors='coerce')
        szum_beker = darab_kimen * (beker_kimen if pd.notnull(beker_kimen) else 0.0)
        
    if szum_elad < 0:
        res = szum_elad - (szum_beker * -1)
    else:
        res = szum_elad - szum_beker
        
    # Is it Alap?
    # Just print the biggest discrepancies or calculate total Res
    # It takes too long to do Termekfajta mapping. Let's just output total res.
    alap_1 += res

print("Total Res Month 1 with new logic:", alap_1)
