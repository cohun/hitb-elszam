import database
import pandas as pd

conn = database.get_connection()
df = pd.read_sql_query("SELECT id, Szla, Befolyt, Resz_fizetett FROM forgalom WHERE Resz_fizetett = 1", conn)
print(f"Resz_fizetett=1 rows: {len(df)}")
if len(df) > 0:
    print(df.head())
    
df2 = pd.read_sql_query("PRAGMA table_info(forgalom)", conn)
print("\nColumns in forgalom:")
print(df2[df2['name'] == 'Resz_fizetett'])
conn.close()
