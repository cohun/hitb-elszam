import pandas as pd
df = pd.read_excel('Excels/Elszám_26.xlsx', sheet_name='ÜK_ELSZÁM')
# Let's see how SzumElad is calculated. Wait, does Elszám_26 have a SumElad tab with raw data?
# Or maybe the data is in "Sheet1" or "ÜK_ELSZÁM". Let's print columns of "Sheet1".
df1 = pd.read_excel('Excels/Elszám_26.xlsx', sheet_name='Sheet1')
print("Sheet1 cols:", df1.columns.tolist())
r = df1[df1['Szla'].astype(str).str.contains('673/2026', na=False)]
for _, row in r.iterrows():
    if 'Előleg' in str(row['Megnevezés']):
        print(f"673/2026 Előleg -> SzumElad: {row.get('SzumElad', 'N/A')}")
        print(f"Külföldi: {row.get('Külföldi ár', 'N/A')}, Árfolyam: {row.get('Árfolyam', 'N/A')}")
