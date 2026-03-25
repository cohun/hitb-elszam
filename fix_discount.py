import database
import pandas as pd

def fix_discount_db():
    print("Kimenő számlák Excel betöltése aszimmetrikus kedvezmények ellenőrzésére...")
    try:
        df_kimen = pd.read_excel('Excels/Kimenő számlák.xls', engine='xlrd')
    except Exception as e:
        print(f"Hiba az Excel betöltésekor: {e}")
        return

    # Kedvezmények kiszámítása számlánként
    invoice_ratios = {}
    for szla, group in df_kimen.groupby('Számla száma'):
        p_val = str(group['Pénznem'].iloc[0]).strip().upper()
        netto_veg = pd.to_numeric(group['Nettó végösszeg'].iloc[0], errors='coerce')
        arfolyam = pd.to_numeric(group['Árfolyam'].iloc[0], errors='coerce')
        if pd.isnull(netto_veg): netto_veg = 0.0
        if pd.isnull(arfolyam): arfolyam = 0.0
        
        calc_sum = 0.0
        for _, r in group.iterrows():
            db = pd.to_numeric(r.get('Mennyiség', 0), errors='coerce')
            if pd.isnull(db): db = 0.0
            
            if p_val and p_val != 'HUF' and arfolyam > 0:
                k_ar = pd.to_numeric(r.get('Külföldi ár', 0), errors='coerce')
                if pd.isnull(k_ar): k_ar = 0.0
                calc_sum += k_ar * db * arfolyam
            else:
                e_ar = pd.to_numeric(r.get('Egységár', 0), errors='coerce')
                if pd.isnull(e_ar): e_ar = 0.0
                calc_sum += e_ar * db
        
        target_netto_huf = netto_veg * arfolyam if (p_val and p_val != 'HUF' and arfolyam > 0) else netto_veg
        
        ratio = 1.0
        if calc_sum != 0 and target_netto_huf != 0 and abs(calc_sum - target_netto_huf) > 2.0:
            ratio = target_netto_huf / calc_sum
            
        if ratio != 1.0:
            invoice_ratios[str(szla)] = ratio
            
    print(f"Talált számlák eltérő aránnyal (kedvezmény/felár): {len(invoice_ratios)} db.")
    if not invoice_ratios:
        print("Nincs javítandó számla.")
        return

    conn = database.get_connection()
    cursor = conn.cursor()
    
    total_updated = 0
    # SQL Update minden eltérő ratio-jú számlára
    for szla, ratio in invoice_ratios.items():
        # Csak akkor szorzunk, ha még nem volt szorozva!
        # De miből tudjuk, hogy már szorozva volt-e az adatbázisban?
        # Lekérdezzük a Sum(Elad*Darab)-ot az adatbázisból, és megnézzük, hogy eltér-e a céltól (Netto vegosszeg).
        
        cursor.execute("SELECT SUM(SzumElad) as current_sum_elad FROM forgalom WHERE Szla = ?", (szla,))
        row = cursor.fetchone()
        current_sum_elad = row[0] if row and row[0] is not None else 0.0
        
        group = df_kimen[df_kimen['Számla száma'] == szla]
        p_val = str(group['Pénznem'].iloc[0]).strip().upper()
        netto_veg = pd.to_numeric(group['Nettó végösszeg'].iloc[0], errors='coerce')
        arfolyam = pd.to_numeric(group['Árfolyam'].iloc[0], errors='coerce')
        if pd.isnull(netto_veg): netto_veg = 0.0
        if pd.isnull(arfolyam): arfolyam = 0.0
        
        target_netto_huf = netto_veg * arfolyam if (p_val and p_val != 'HUF' and arfolyam > 0) else netto_veg
        
        if current_sum_elad != 0 and abs(current_sum_elad - target_netto_huf) > 2.0:
            # Tényleg rossz a DB-ben is, javítjuk!
            # Itt abból indulunk ki, hogy az Elad az eredeti (Külföldi_ár * Árfolyam vagy Egységár). 
            # Tehát az adatbázisbeli Elad_ar-at is felülírjuk az aránnyal, ha eddig nem volt.
            
            # 1. Elad frissítése ratio-val
            cursor.execute("UPDATE forgalom SET Elad = Elad * ? WHERE Szla = ?", (ratio, szla))
            
            # 2. SzumElad = Elad * Darab
            cursor.execute("UPDATE forgalom SET SzumElad = Elad * Darab WHERE Szla = ?", (szla,))
            
            # 3. Jutalek és Res frissítése
            cursor.execute('UPDATE forgalom SET Jut = SzumElad * ("Jut_%" / 100.0) WHERE Szla = ?', (szla,))
            cursor.execute('UPDATE forgalom SET Rés = IFNULL(SzumElad, 0) - IFNULL(SzumBeker, 0) WHERE Szla = ?', (szla,))
            
            total_updated += 1
            
    conn.commit()
    conn.close()
    
    print(f"Javítva: {total_updated} számlán a kedvezmények szétosztásra kerültek az adatbázisban.")

if __name__ == '__main__':
    fix_discount_db()
