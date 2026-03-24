import database

def fix_db():
    conn = database.get_connection()
    cursor = conn.cursor()
    
    # Kijavítjuk a SzumBeker értékeket azokban a sorokban, ahol volt bekerár
    cursor.execute('''
        UPDATE forgalom
        SET SzumBeker = Darab * Beker
        WHERE Beker IS NOT NULL
    ''')
    
    szum_beker_updated = cursor.rowcount
    
    # Újrakalkuláljuk a Rés értéket a javított SzumBeker és a SzumElad adatok alapján
    cursor.execute('''
        UPDATE forgalom
        SET Rés = CASE 
            WHEN SzumElad < 0 THEN SzumElad - (SzumBeker * -1)
            ELSE SzumElad - SzumBeker
        END
    ''')
    
    res_updated = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"Javítva: {szum_beker_updated} sor SzumBeker frissült.")
    print(f"Javítva: {res_updated} sor Rés frissült.")

if __name__ == '__main__':
    fix_db()
