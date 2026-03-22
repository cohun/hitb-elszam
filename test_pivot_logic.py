import sqlite3
import pandas as pd
import numpy as np

conn = sqlite3.connect('hitb_database.db')
df = pd.read_sql_query("SELECT * FROM forgalom", conn)

df['Termékfajta'] = df['Termékfajta'].fillna('Ismeretlen')
df['Termékkör'] = df['Termékkör'].fillna('Ismeretlen')

# Group by Főcsoport (Termékfajta) and Kelt_hó
pivot = pd.pivot_table(
    df, values='Rés', index=['Termékfajta', 'Termékkör'], columns='Kelt_hó',
    aggfunc='sum', fill_value=0, margins=True, margins_name='Grand Total'
)

# Print for 'Alap' explicitly
for (tk, tf), row in pivot.iterrows():
    if tk == 'Alap':
        print(f"{tf[:20]:20s} | {row.get(1.0, 0):15.2f} | {row.get(2.0, 0):15.2f} | {row.get('Grand Total', 0):15.2f}")
    if tk == 'Grand Total':
        print(f"GRAND TOTAL          | {row.get(1.0, 0):15.2f} | {row.get(2.0, 0):15.2f} | {row.get('Grand Total', 0):15.2f}")

conn.close()
