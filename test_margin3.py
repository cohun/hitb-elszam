import pandas as pd
import numpy as np

kimen = pd.read_excel('Excels/Kimenő számlák.xls', engine='xlrd')
kimen['Dátum'] = pd.to_datetime(kimen['Dátum'], errors='coerce')

alap_old = 0
alap_new_if = 0

for idx, row in kimen.iterrows():
    if row['Dátum'].month != 1: continue
    
    # We don't have exact Termekfajta, but we can just sum ALL Res and compare to Grand Total Month 1 (38,248,483)
    darab = pd.to_numeric(row.get('Mennyiség', 0), errors='coerce')
    elad = pd.to_numeric(row.get('Egységár', 0), errors='coerce')
    beker = pd.to_numeric(row.get('Átlag bekerár', 0), errors='coerce')
    
    if pd.isnull(darab): darab = 0.0
    if pd.isnull(elad): elad = 0.0
    if pd.isnull(beker): beker = 0.0
    
    szum_elad = darab * elad
    szum_beker = darab * beker
    
    res_old = szum_elad - szum_beker
    alap_old += res_old
    
    if szum_elad < 0:
        res_new = szum_elad - (szum_beker * -1)
    else:
        res_new = szum_elad - szum_beker
    
    alap_new_if += res_new

print("Total Res Month 1 (OLD):", alap_old)
print("Total Res Month 1 (NEW IF):", alap_new_if)
