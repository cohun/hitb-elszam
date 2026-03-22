import pandas as pd
import numpy as np
import warnings
from datetime import datetime
import database

# openpyxl figyelmeztetések kikapcsolása
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

EXCELS_DIR = '/Users/attila/Dev/H-ITB Elszámolás/Excels'
ALAP_PATH = f'{EXCELS_DIR}/alap_26.xlsx'
KIMENO_PATH = f'{EXCELS_DIR}/Kimenő számlák.xls'
ELABE_PATH = f'{EXCELS_DIR}/Elabe_lista.xls'

def clean_dict(series_k, series_v):
    d = {}
    for k, v in zip(series_k, series_v):
        if pd.notna(k) and pd.notna(v):
            try: k_int = str(int(k))
            except: k_int = str(k).strip()
            d[k_int] = str(v).strip()
    return d

def load_mappings():
    """A lookup táblák kinyerése az alap_26.xlsx Sheet1 fülről dinamikusan."""
    df1 = pd.read_excel(ALAP_PATH, sheet_name='Sheet1')
    t2 = clean_dict(df1.iloc[:, 0], df1.iloc[:, 1]) # Item -> ProductGroup
    t6 = clean_dict(df1.iloc[:, 5], df1.iloc[:, 6]) # Item.1 -> ProductGroup.1
    t7 = clean_dict(df1.iloc[:, 14], df1.iloc[:, 15]) # Item.2 -> ProductKind.3
    
    # Készítünk egy mappolást Termékkör -> Termékfajta-re (pl. Table8)
    # df1.iloc[:, 1] -> df1.iloc[:, 2] (ProductGroup -> ProductKind)
    group_to_kind = {}
    for g, k in zip(df1.iloc[:, 1], df1.iloc[:, 2]):
        if pd.notna(g) and pd.notna(k):
            group_to_kind[str(g).strip()] = str(k).strip()
            
    # T6 cuccokat is berakjuk a group_to_kind-ba
    for g, k in zip(df1.iloc[:, 6], df1.iloc[:, 7]):
        if pd.notna(g) and pd.notna(k):
            group_to_kind[str(g).strip()] = str(k).strip()
            
    return t2, t6, t7, group_to_kind

def get_termekkor(cikk, t2, t6):
    cikk_str = str(cikk).strip()
    if cikk_str.startswith("210"):
        val = cikk_str[:4]
        return t6.get(val, "Ismeretlen")
    else:
        prefix = cikk_str[:2]
        return t2.get(prefix, "Előleg")

def get_termekfajta(cikk, megnevezes, termekkor, t7, group_to_kind):
    cikk_str = str(cikk).strip()
    megn_str = str(megnevezes).strip()
    
    if not cikk_str or cikk_str.lower() == 'nan':
        return "Előleg"
        
    text_before = cikk_str.split('/')[0] if '/' in cikk_str else cikk_str
    
    if text_before == "143" or text_before == "144":
        return "Egyéb"
        
    if cikk_str.startswith("131"):
        return t7.get(text_before, "Ismeretlen")
        
    if megn_str.startswith("Előleg"):
        return "Előleg"
        
    return group_to_kind.get(termekkor, "Ismeretlen")

def process_and_import():
    try:
        print("Térképező táblák betöltése az alap_26.xlsx-ből...")
        t2, t6, t7, group_to_kind = load_mappings()
        
        print(f"Kimenő számlák betöltése... ({KIMENO_PATH})")
        # xlrd error esetén a .xls fájlokat is pandas képes beolvasni, de engine='xlrd' kell. 
        # Excel hiba ("SSCS size is 0") miatt openpyxl nem olvassa a régi .xls-t, de pandas az xlrd-vel igen.
        df_kimen = pd.read_excel(KIMENO_PATH, engine='xlrd')
        
        print(f"Elábé lista betöltése... ({ELABE_PATH})")
        df_elabe = pd.read_excel(ELABE_PATH, engine='xlrd')
        
        # Melyik számlák vannak már az adatbázisban?
        existing_invoices = database.get_existing_invoices()
        
        # 1. Befolyt státusz frissítés a meglévő rekordokhoz
        # Szabály: Ha a Kifizetett összeg >= Bruttó végösszeg -> 'i' különben 'n'
        status_updates = {}
        for _, row in df_kimen.iterrows():
            szla = str(row['Számla száma'])
            if szla in existing_invoices:
                kif = pd.to_numeric(row['Kifizetett összeg'], errors='coerce') or 0
                brutto = pd.to_numeric(row['Bruttó végösszeg'], errors='coerce') or 0
                status_updates[szla] = 'i' if kif >= brutto else 'n'
                
        if status_updates:
            print(f"{len(status_updates)} meglévő számla 'Befolyt' státuszának frissítése...")
            database.update_befolyt_status(status_updates)
            
        # 1.5. ÜK_kifizet_hó értékeinek frissítése az Elszám_26.xlsx fájlból
        print("ÜK_kifizet_hó adatok szinkronizálása (Elszám_26.xlsx)...")
        ELSZAM_PATH = f'{EXCELS_DIR}/Elszám_26.xlsx'
        try:
            df_elszam = pd.read_excel(ELSZAM_PATH, sheet_name='Sheet1')
            
            # Kiszűrjük, ahol ki van töltve a Column1
            if 'Column1' in df_elszam.columns and 'Szla' in df_elszam.columns:
                valid_elszam = df_elszam.dropna(subset=['Column1'])
                if not valid_elszam.empty:
                    # Szótárt építünk: Szla -> Column1 érték
                    uk_kifizet_updates = {}
                    for _, row in valid_elszam.iterrows():
                        szla = str(row['Szla']).strip()
                        val = row['Column1']
                        # Numerikus cella konvertálása, pl. 1.0 -> '1'
                        try:
                            val_str = str(int(val))
                        except Exception:
                            val_str = str(val).strip()
                        uk_kifizet_updates[szla] = val_str
                        
                    if uk_kifizet_updates:
                        # Frissítjük a DB-t SQL commandon keresztül
                        conn = database.get_connection()
                        cursor = conn.cursor()
                        print(f"{len(uk_kifizet_updates)} számla ÜK_kifizet_hó értékének frissítése...")
                        for sz, k_val in uk_kifizet_updates.items():
                            cursor.execute('UPDATE forgalom SET "ÜK_kifizet_hó" = ? WHERE Szla = ?', (k_val, sz))
                        conn.commit()
                        conn.close()
        except Exception as sheet_err:
            print(f"Figyelem: Az Elszám_26.xlsx Sheet1 olvasása közben hiba (üres fájl vagy más oszlopok okán): {sheet_err}")

        # 2. Új számlák kiszűrése és adatbázisba rendezése
        new_kimen = df_kimen[~df_kimen['Számla száma'].astype(str).isin(existing_invoices)]
        
        if new_kimen.empty:
            print("Nincs új beszívandó számla.")
            return True, "Zökkenőmentes frissítés: nincs új számla, státuszok és kifizetési hók frissítve."
            
        print(f"{len(new_kimen['Számla száma'].unique())} új számla feldolgozása...")
        
        # Eredmény Dataframe összeállítása
        result_rows = []
        for _, krow in new_kimen.iterrows():
            szla = str(krow.get('Számla száma', ''))
            cikk = str(krow.get('Cikkszám', ''))
            
            # Kikeressük az Elábé-ből a vonatkozó sort:
            # Match by Bizonylatszám AND Cikkszám
            erows = df_elabe[(df_elabe['Bizonylatszám'].astype(str) == szla) & 
                             (df_elabe['Cikkszám'].astype(str) == cikk)]
                             
            teljesites = krow.get('Dátum', None) # Fallback ha nincs Elabe teljesítés
            if not erows.empty:
                teljesites = erows.iloc[0].get('Teljesítés', teljesites)
                
            datum = pd.to_datetime(krow.get('Dátum', None), errors='coerce')
            teljesites = pd.to_datetime(teljesites, errors='coerce')
            
            kelt_ho = datum.month if pd.notnull(datum) else None
            telj_ho = teljesites.month if pd.notnull(teljesites) else None
            
            megnevezes = krow.get('Megnevezés', '')
            termekkor = get_termekkor(cikk, t2, t6)
            termekfajta = get_termekfajta(cikk, megnevezes, termekkor, t7, group_to_kind)
            
            darab = pd.to_numeric(krow.get('Mennyiség', 0), errors='coerce')
            beker_ar = pd.to_numeric(krow.get('Átlag bekerár', 0), errors='coerce')
            szum_beker = darab * beker_ar
            
            elad_ar = pd.to_numeric(krow.get('Egységár', 0), errors='coerce')
            szum_elad = elad_ar * darab if pd.notnull(darab) else 0
            
            jut_szaz = pd.to_numeric(krow.get('Jutalék %', 0), errors='coerce')
            jutalek = szum_elad * (jut_szaz / 100.0) if pd.notnull(jut_szaz) else 0
            
            res = szum_elad - szum_beker
                
            kif = pd.to_numeric(krow.get('Kifizetett összeg', 0), errors='coerce')
            brutto = pd.to_numeric(krow.get('Bruttó végösszeg', 0), errors='coerce')
            befolyt = 'i' if kif >= brutto else 'n'
            
            res_row = {
                'Szla': szla,
                'Vevő': krow.get('Vevő neve', ''),
                'Dátum': datum.date() if pd.notnull(datum) else None,
                'Kelt_hó': kelt_ho,
                'Teljesítés': teljesites.date() if pd.notnull(teljesites) else None,
                'Telj_hó': telj_ho,
                'Cikk': cikk,
                'Termékkör': termekkor,
                'Termékfajta': termekfajta,
                'Megnevezés': megnevezes,
                'Darab': darab,
                'Beker': beker_ar,
                'SzumBeker': szum_beker,
                'KülföldiÁr': krow.get('Külföldi ár', 0),
                'Pénznem': krow.get('Pénznem', ''),
                'Árfolyam': krow.get('Árfolyam', 0),
                'Listaár': krow.get('Listaár', 0),
                'Elad': elad_ar,
                'SzumElad': szum_elad,
                'Jut_%': jut_szaz,
                'Jut': jutalek,
                'ÜK': krow.get('Üzletkötő', ''),
                'Rés': res,
                'Befolyt': befolyt,
                # Custom defaults will be NULL in DB
            }
            result_rows.append(res_row)
            
        if result_rows:
            df_result = pd.DataFrame(result_rows)
            database.insert_new_records(df_result)
            return True, f"Sikeres frissítés: {len(df_result)} új sor került az adatbázisba!"
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Hiba történt a beszippantás során: {str(e)}"
        
if __name__ == '__main__':
    database.init_db()
    success, msg = process_and_import()
    print(msg)
