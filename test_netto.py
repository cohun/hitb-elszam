import pandas as pd
import numpy as np

df = pd.read_excel('Excels/Kimenő számlák.xls', engine='xlrd')

def test_inv(szla):
    d = df[df['Számla száma'] == szla]
    if d.empty: return
    p = d['Pénznem'].iloc[0]
    n = d['Nettó végösszeg'].iloc[0]
    a = d['Árfolyam'].iloc[0]
    
    s1 = (pd.to_numeric(d['Egységár'], errors='coerce').fillna(0) * pd.to_numeric(d['Mennyiség'], errors='coerce').fillna(0)).sum()
    s2 = (pd.to_numeric(d['Külföldi ár'], errors='coerce').fillna(0) * pd.to_numeric(d['Mennyiség'], errors='coerce').fillna(0)).sum()
    
    print(f"Szla: {szla}")
    print(f"  Pénznem: {p}, Nettó_vég: {n}, Árfolyam: {a}")
    print(f"  Sum(Egységár*Darab): {s1}")
    print(f"  Sum(Külfár*Darab): {s2}")
    
test_inv('24/2026')
test_inv('475/2026')
test_inv('476/2026')
