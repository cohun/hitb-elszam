import pandas as pd

# Dummy data
data = {
    'Termékkör': ['Alap', 'Alap', 'Alap', 'Beruházás', 'Beruházás', 'Egyéb'],
    'Termékfajta': ['A', 'A', 'B', 'X', 'Y', 'Z'],
    'Kelt_hó': [1, 2, 1, 1, 2, 2],
    'Rés': [100, 200, 50, 300, 400, -50]
}
pdf = pd.DataFrame(data)

pivot_main = pd.pivot_table(pdf, values='Rés', index='Termékkör', columns='Kelt_hó', aggfunc='sum', fill_value=0, margins=True, margins_name='Grand Total')
pivot_detail = pd.pivot_table(pdf, values='Rés', index=['Termékkör', 'Termékfajta'], columns='Kelt_hó', aggfunc='sum', fill_value=0, margins=True, margins_name='Grand Total')

rows = []
for idx, row in pivot_main.iterrows():
    if idx == 'Grand Total':
        continue
    # Add main row
    r = row.to_dict()
    r['Szum of Árrés'] = f"🔹 {idx} összesen"
    rows.append(r)
    
    # Add detail rows
    if idx in pivot_detail.index.get_level_values(0):
        details = pivot_detail.loc[idx]
        for d_idx, d_row in details.iterrows():
            if d_idx == 'Grand Total': continue # Exclude detail margins if they exist
            dr = d_row.to_dict()
            dr['Szum of Árrés'] = f"    {d_idx}" # Use non-breaking spaces
            rows.append(dr)

gt = pivot_main.loc['Grand Total'].to_dict()
gt['Szum of Árrés'] = "Grand Total"
rows.append(gt)

final_df = pd.DataFrame(rows)
final_df = final_df.set_index('Szum of Árrés')
final_df = final_df.fillna(0).astype(int)
print(final_df)
