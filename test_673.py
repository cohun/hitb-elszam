import pandas as pd
kimen = pd.read_excel('Excels/Kimenő számlák.xls', engine='xlrd')
kimen['szla_str'] = kimen['Számla száma'].astype(str).str.strip()
row = kimen[kimen['szla_str'] == '673/2026']
for idx, r in row.iterrows():
    print(f"Számla: {r['szla_str']}, Pénznem: {r['Pénznem']}, Árfolyam: {r['Árfolyam']}")
    print(f"Mennyiség: {r['Mennyiség']}, Egységár: {r['Egységár']}")
    print(f"Bruttó érték: {r.get('Bruttó érték', 'N/A')}")
