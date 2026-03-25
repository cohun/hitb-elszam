import database

def fix_storno_res_db():
    conn = database.get_connection()
    cursor = conn.cursor()
    
    # 1. Rés frissítése Sima kivonással, a hibás CASE eltávolításával
    cursor.execute('''
        UPDATE forgalom
        SET Rés = IFNULL(SzumElad, 0) - IFNULL(SzumBeker, 0)
    ''')
    res_updated = cursor.rowcount
    
    conn.commit()
    conn.close()
    
    print(f"Javítva: {res_updated} sor Rés frissült a teljes adatbázisban a helyes logikával.")

if __name__ == '__main__':
    fix_storno_res_db()
