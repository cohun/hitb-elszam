import database

def fix_currency_db():
    conn = database.get_connection()
    cursor = conn.cursor()
    
    # 1. Elad frissítése (KülföldiÁr * Árfolyam)
    cursor.execute('''
        UPDATE forgalom
        SET Elad = KülföldiÁr * Árfolyam
        WHERE Pénznem IS NOT NULL 
          AND Pénznem != 'HUF' 
          AND Pénznem != '' 
          AND Árfolyam > 0
          AND KülföldiÁr != 0
    ''')
    elad_updated = cursor.rowcount
    
    # 2. SzumElad frissítése (Elad * Darab)
    cursor.execute('''
        UPDATE forgalom
        SET SzumElad = Elad * Darab
        WHERE Pénznem IS NOT NULL 
          AND Pénznem != 'HUF' 
          AND Pénznem != '' 
          AND Árfolyam > 0
          AND KülföldiÁr != 0
    ''')
    szum_elad_updated = cursor.rowcount
    
    # 3. Jut frissítése (SzumElad * (Jut_% / 100))
    cursor.execute('''
        UPDATE forgalom
        SET Jut = SzumElad * ("Jut_%" / 100.0)
        WHERE Pénznem IS NOT NULL 
          AND Pénznem != 'HUF' 
          AND Pénznem != '' 
          AND Árfolyam > 0
          AND KülföldiÁr != 0
          AND "Jut_%" IS NOT NULL
    ''')
    jut_updated = cursor.rowcount
    
    # 4. Rés frissítése
    cursor.execute('''
        UPDATE forgalom
        SET Rés = CASE 
            WHEN SzumElad < 0 THEN SzumElad - (SzumBeker * -1)
            ELSE SzumElad - SzumBeker
        END
        WHERE Pénznem IS NOT NULL 
          AND Pénznem != 'HUF' 
          AND Pénznem != '' 
          AND Árfolyam > 0
          AND KülföldiÁr != 0
    ''')
    res_updated = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"Javítva: {elad_updated} sor Elad frissült.")
    print(f"Javítva: {szum_elad_updated} sor SzumElad frissült.")
    print(f"Javítva: {jut_updated} sor Jut frissült.")
    print(f"Javítva: {res_updated} sor Rés frissült.")

if __name__ == '__main__':
    fix_currency_db()
