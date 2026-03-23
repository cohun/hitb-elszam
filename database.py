import sqlite3
import pandas as pd
from typing import List

DB_PATH = 'hitb_database.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    """Inicializálja az adatbázist és létrehozza a forgalom táblát."""
    conn = get_connection()
    cursor = conn.cursor()
    
    # Létrehozzuk a táblát, ha még nem létezik. 
    # Primary key egy belső id, mivel egy Szla (számla) több sort is jelenthet.
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS forgalom (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            Szla TEXT,
            Vevő TEXT,
            Dátum DATE,
            Kelt_hó INTEGER,
            Teljesítés DATE,
            Telj_hó INTEGER,
            Cikk TEXT,
            Termékkör TEXT,
            Termékfajta TEXT,
            Megnevezés TEXT,
            Darab REAL,
            Beker REAL,
            SzumBeker REAL,
            KülföldiÁr REAL,
            Pénznem TEXT,
            Árfolyam REAL,
            Listaár REAL,
            Elad REAL,
            SzumElad REAL,
            "Jut_%" REAL,
            Jut REAL,
            ÜK TEXT,
            Rés REAL,
            Befolyt TEXT,
            
            -- Lokális / Egyedi mezők amik nem íródnak felül a törzs adatokkal
            "ÜK_kifizet_hó" TEXT,
            "KülföldEUR" REAL,
            "Jut_modositott" INTEGER DEFAULT 0
        )
    ''')
    
    # Index létrehozása a gyorsabb kereséshez Szla alapján
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_szla ON forgalom(Szla)')
    
    # 1. Munkafolyamat: ÜK mentési tábla
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uk_settings (
            uk_name TEXT PRIMARY KEY,
            is_active INTEGER
        )
    ''')
    # 3. Munkafolyamat: KTGC beállítások
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uk_ktgc (
            uk_name TEXT PRIMARY KEY,
            ossz_terv REAL DEFAULT 0,
            alap_terv REAL DEFAULT 0,
            beruhazas_terv REAL DEFAULT 0,
            alap_limit REAL DEFAULT 0,
            bonusz_limit REAL DEFAULT 0
        )
    ''')
    
    conn.commit()
    conn.close()

def get_existing_invoices() -> set:
    """Visszaadja a már adatbázisban lévő számlaszámok halmazát."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT Szla FROM forgalom')
    rows = cursor.fetchall()
    conn.close()
    return {row[0] for row in rows}

def insert_new_records(df: pd.DataFrame):
    """Beszúrja az új rekordokat."""
    if df.empty:
        return
    conn = get_connection()
    # A pandas to_sql használata append móddal
    df.to_sql('forgalom', conn, if_exists='append', index=False)
    conn.close()

def update_befolyt_status(szla_status_dict: dict):
    """
    Frissíti a Befolyt mezőt a meglévő rekordoknál.
    A dictionary formátuma bemenetként: { 'Szla_szám': 'Befolyt_érték' }
    """
    if not szla_status_dict:
        return
        
    conn = get_connection()
    cursor = conn.cursor()
    
    # SQLite update végrehajtása
    for szla, new_status in szla_status_dict.items():
        cursor.execute('''
            UPDATE forgalom
            SET Befolyt = ?
            WHERE Szla = ?
        ''', (new_status, szla))
        
    conn.commit()
    conn.close()

def load_data_for_ui() -> pd.DataFrame:
    """Visszaadja az összes adatot a UI számára egy Pandas DataFrame-ben."""
    conn = get_connection()
    query = 'SELECT * FROM forgalom'
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

def update_custom_fields(record_id: int, uk_kifizet_ho_val: str, kulfold_eur_val: float):
    """Frissíti egy adott rekord egyedi mezőit az asztali felületről."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE forgalom
        SET "ÜK_kifizet_hó" = ?,
            "KülföldEUR" = ?
        WHERE id = ?
    ''', (uk_kifizet_ho_val, kulfold_eur_val, record_id))
    conn.commit()
    conn.close()

def mass_update_kifizet_ho(record_ids: list, new_ho: str):
    """Tömegesen frissíti a megadott azonosítójú rekordok kifizetési hónapját."""
    if not record_ids:
        return
    conn = get_connection()
    cursor = conn.cursor()
    placeholders = ','.join('?' for _ in record_ids)
    cursor.execute(f'''
        UPDATE forgalom
        SET "ÜK_kifizet_hó" = ?
        WHERE id IN ({placeholders})
    ''', [new_ho] + record_ids)
    conn.commit()
    conn.close()

def update_jutalek(record_id: int, new_jut_szaz: float, new_jut: float):
    """Frissíti a módosított jutalékot és beállítja a flaget."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE forgalom
        SET "Jut_%" = ?,
            "Jut" = ?,
            "Jut_modositott" = 1
        WHERE id = ?
    ''', (new_jut_szaz, new_jut, record_id))
    conn.commit()
    conn.close()

def update_jutalek_es_uk(record_id: int, new_jut_szaz: float, new_jut: float, new_uk: str):
    """Frissíti a módosított jutalékot, az üzletkötőt, és beállítja a flaget."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE forgalom
        SET "Jut_%" = ?,
            "Jut" = ?,
            "ÜK" = ?,
            "Jut_modositott" = 1
        WHERE id = ?
    ''', (new_jut_szaz, new_jut, new_uk, record_id))
    conn.commit()
    conn.close()

def get_active_uks() -> list:
    """Visszaadja az aktív üzletkötők listáját, vagy None-t ha még nem volt mentve lista."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM uk_settings')
    if cursor.fetchone()[0] == 0:
        conn.close()
        return None
    cursor.execute('SELECT uk_name FROM uk_settings WHERE is_active = 1')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def set_active_uks(active_list: list, all_uks: list):
    """Elmenti mely üzletkötők aktívak és melyek nem."""
    conn = get_connection()
    cursor = conn.cursor()
    for uk in all_uks:
        is_active = 1 if uk in active_list else 0
        cursor.execute('''
            INSERT OR REPLACE INTO uk_settings (uk_name, is_active)
            VALUES (?, ?)
        ''', (uk, is_active))
    conn.commit()
    conn.close()

def get_ktgc_settings(uk_name: str) -> dict:
    """Lekéri egy ÜK KTGC beállításait, vagy alapértelmezett 0-kat ad vissza."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT ossz_terv, alap_terv, beruhazas_terv, alap_limit, bonusz_limit FROM uk_ktgc WHERE uk_name = ?', (uk_name,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return {
            'ossz_terv': row[0],
            'alap_terv': row[1],
            'beruhazas_terv': row[2],
            'alap_limit': row[3],
            'bonusz_limit': row[4]
        }
    return {
        'ossz_terv': 0.0,
        'alap_terv': 0.0,
        'beruhazas_terv': 0.0,
        'alap_limit': 0.0,
        'bonusz_limit': 0.0
    }

def save_ktgc_settings(uk_name: str, settings: dict):
    """Elmenti vagy frissíti egy ÜK KTGC beállításait."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO uk_ktgc (uk_name, ossz_terv, alap_terv, beruhazas_terv, alap_limit, bonusz_limit)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (
        uk_name, 
        settings.get('ossz_terv', 0.0), 
        settings.get('alap_terv', 0.0), 
        settings.get('beruhazas_terv', 0.0), 
        settings.get('alap_limit', 0.0), 
        settings.get('bonusz_limit', 0.0)
    ))
    conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
    print("Adatbázis inicializálva.")
