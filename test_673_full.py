import pandas as pd
kimen = pd.read_excel('Excels/Kimenő számlák.xls', engine='xlrd')
kimen['szla_str'] = kimen['Számla száma'].astype(str).str.strip()
row = kimen[kimen['szla_str'] == '673/2026']
for idx, r in row.iterrows():
    if 'Előleg' in str(r['Megnevezés']):
        for c in row.columns:
            print(f"{c}: {r[c]}")
        break
