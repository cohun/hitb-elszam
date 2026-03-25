import pandas as pd
import numpy as np
import warnings
from datetime import datetime
import database

# openpyxl figyelmeztetések kikapcsolása
warnings.filterwarnings('ignore', category=UserWarning, module='openpyxl')

EXCELS_DIR = 'Excels'
ALAP_PATH = f'{EXCELS_DIR}/alap_26.xlsx'
KIMENO_PATH = f'{EXCELS_DIR}/Kimenő számlák.xls'
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
        
        # Kifizetett és kifizetetlen eredeti számlák kigyűjtése a sztornók pontosabb kezeléséhez
        paid_invoices_info = set()
        unpaid_invoices_info = set()
        for _, row in df_kimen.iterrows():
            kif_val = pd.to_numeric(row.get('Kifizetett összeg', 0), errors='coerce')
            brutto_val = pd.to_numeric(row.get('Bruttó végösszeg', 0), errors='coerce')
            if pd.isna(kif_val): kif_val = 0.0
            if pd.isna(brutto_val): brutto_val = 0.0
            if brutto_val > 0:
                vevo_name = str(row.get('Vevő neve', '')).strip()
                if kif_val >= brutto_val:
                    paid_invoices_info.add((vevo_name, brutto_val))
                else:
                    unpaid_invoices_info.add((vevo_name, brutto_val))

        def get_befolyt_status(r_kif, r_brutto, r_vevo):
            k_val = pd.to_numeric(r_kif, errors='coerce')
            b_val = pd.to_numeric(r_brutto, errors='coerce')
            if pd.isna(k_val): k_val = 0.0
            if pd.isna(b_val): b_val = 0.0
            if b_val < 0:
                # Sztornó számla logikája
                v_name = str(r_vevo).strip()
                t_brutto = -b_val
                # Ha van ugyanilyen összegű kifizetetlen eredeti számla, akkor a sztornó ahhoz tartozik:
                if (v_name, t_brutto) in unpaid_invoices_info:
                    return 'n'
                elif (v_name, t_brutto) in paid_invoices_info:
                    return 'i'
                else:
                    return 'n'
            return 'i' if k_val >= b_val else 'n'

        # 1. Befolyt státusz frissítés a meglévő rekordokhoz
        status_updates = {}
        for _, row in df_kimen.iterrows():
            szla = str(row['Számla száma'])
            if szla in existing_invoices:
                status_updates[szla] = get_befolyt_status(row.get('Kifizetett összeg', 0), row.get('Bruttó végösszeg', 0), row.get('Vevő neve', ''))
                
        if status_updates:
            print(f"{len(status_updates)} meglévő számla 'Befolyt' státuszának frissítése...")
            database.update_befolyt_status(status_updates)
            


        # 2. Új számlák kiszűrése és adatbázisba rendezése
        new_kimen = df_kimen[~df_kimen['Számla száma'].astype(str).isin(existing_invoices)]
        
        if new_kimen.empty:
            print("Nincs új beszívandó számla.")
            return True, "Zökkenőmentes frissítés: nincs új számla, státuszok és kifizetési hók frissítve."
            
        print(f"{len(new_kimen['Számla száma'].unique())} új számla feldolgozása...")
        
        # Kedvezmények kiszámítása számlánként (arányosítás)
        invoice_ratios = {}
        for szla, group in new_kimen.groupby('Számla száma'):
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
            if calc_sum != 0 and target_netto_huf != 0 and abs(calc_sum - target_netto_huf) > 2.0: # Minimális kerekítési hibát engedünk
                ratio = target_netto_huf / calc_sum
                
            invoice_ratios[str(szla)] = ratio
        
        # Eredmény Dataframe összeállítása
        result_rows = []
        for _, krow in new_kimen.iterrows():
            szla = str(krow.get('Számla száma', ''))
            ratio = invoice_ratios.get(szla, 1.0)
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
            if pd.isnull(darab): darab = 0.0
            
            szum_beker = 0.0
            beker_ar = 0.0
            
            if not erows.empty:
                teljesites = erows.iloc[0].get('Teljesítés', teljesites)
                szum_beker_temp = 0.0
                sum_darab_elabe = 0.0
                
                for _, erow in erows.iterrows():
                    e_menny = pd.to_numeric(erow.get('Mennyiség', 0), errors='coerce')
                    if pd.isnull(e_menny): e_menny = 0.0
                    
                    e_beker = pd.to_numeric(erow.get('Bekerár', 0), errors='coerce')
                    if pd.isnull(e_beker) or e_beker == 0.0:
                        e_beker = pd.to_numeric(erow.get('Átlag bekerár', erow.get('Egységár', 0)), errors='coerce')
                    if pd.isnull(e_beker): e_beker = 0.0
                        
                    szum_beker_temp += (e_menny * e_beker)
                    sum_darab_elabe += e_menny
                    
                if szum_beker_temp > 0:
                    beker_ar = szum_beker_temp / sum_darab_elabe if sum_darab_elabe > 0 else 0.0
                    szum_beker = darab * beker_ar
            
            # Fallback a kimenő számlából, ha az Elábé üres vagy nullás értéket adott
            if szum_beker == 0.0:
                beker_ar = pd.to_numeric(krow.get('Átlag bekerár', 0), errors='coerce')
                if pd.isnull(beker_ar): beker_ar = 0.0
                szum_beker = darab * beker_ar
            
            elad_ar = pd.to_numeric(krow.get('Egységár', 0), errors='coerce')
            if pd.isnull(elad_ar): elad_ar = 0.0
            
            penznem = str(krow.get('Pénznem', '')).strip().upper()
            kulf_ar = pd.to_numeric(krow.get('Külföldi ár', 0), errors='coerce')
            arfolyam = pd.to_numeric(krow.get('Árfolyam', 0), errors='coerce')
            if pd.isnull(kulf_ar): kulf_ar = 0.0
            if pd.isnull(arfolyam): arfolyam = 0.0
            
            # Külföldi pénznem esetén az Excelben sokszor hibás a forint 'Egységár' 
            # (múltbeli árfolyammal számol), ezért mindig újrakalkuláljuk.
            if penznem and penznem != 'HUF' and arfolyam > 0 and kulf_ar != 0:
                elad_ar = kulf_ar * arfolyam
                
            # Átvételi és számlavégi kedvezmény arányosítása (ratio)
            elad_ar = elad_ar * ratio
            
            szum_elad = elad_ar * darab
            
            jut_szaz = pd.to_numeric(krow.get('Jutalék %', 0), errors='coerce')
            if pd.isnull(jut_szaz): jut_szaz = 0.0
            jutalek = szum_elad * (jut_szaz / 100.0)
            
            # A képlet: Rés = SzumElad - SzumBeker.
            # (Stornó számláknál a Darab eleve negatív, emiatt mindkét érték negatív, így a kivonás automatikusan helyes marad!)
            res = szum_elad - szum_beker
                
            befolyt = get_befolyt_status(krow.get('Kifizetett összeg', 0), krow.get('Bruttó végösszeg', 0), krow.get('Vevő neve', ''))
            
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
            print(f"Sikeres frissítés: {len(df_result)} új sor került az adatbázisba!")
        
        # 1.5. (illetve most már 3.) ÜK_kifizet_hó értékeinek frissítése az Elszám_26.xlsx fájlból
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
                        print(f"{len(uk_kifizet_updates)} számla ÜK_kifizet_hó értékének frissítési kísérlete (csak üres mezőknél)...")
                        for sz, k_val in uk_kifizet_updates.items():
                            cursor.execute('''
                                UPDATE forgalom 
                                SET "ÜK_kifizet_hó" = ? 
                                WHERE Szla = ? AND ("ÜK_kifizet_hó" IS NULL OR "ÜK_kifizet_hó" = '')
                            ''', (k_val, sz))
                        conn.commit()
                        conn.close()
        except Exception as sheet_err:
            print(f"Figyelem: Az Elszám_26.xlsx Sheet1 olvasása közben hiba (üres fájl vagy más oszlopok okán): {sheet_err}")
            
        if result_rows:
            return True, f"Sikeres frissítés: {len(df_result)} új sor került az adatbázisba, és {len(uk_kifizet_updates) if 'uk_kifizet_updates' in locals() else 0} számla fizetési hónapja szinkronizálva!"
        else:
            return True, "Zökkenőmentes frissítés: nincs új számla, de a státuszok és a fizetési hónapok szinkronizálva lettek!"
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Hiba történt a beszippantás során: {str(e)}"
        
if __name__ == '__main__':
    database.init_db()
    success, msg = process_and_import()
    print(msg)
