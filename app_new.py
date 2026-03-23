import streamlit as st
import pandas as pd
import database
import data_importer
import time

# --- Oldal beállítások ---
st.set_page_config(page_title="H-ITB Elszámolás", layout="wide")
st.title("📊 H-ITB Elszámolás Kezelő")

# Inicializálás
database.init_db()

# --- Függvény az adatok frissítéséhez az UI-ból ---
@st.cache_data(ttl=1) # Cache trükk hogy azonnal lássuk a módosítást
def get_data():
    return database.load_data_for_ui()

# --- Sidebar: Műveletek ---
with st.sidebar:
    st.header("��️ Nézet Választó")
    view_mode = st.radio("Válassz nézetet:", ["📊 Fő Dashboard", "📑 1. Munkafolyamat (ÜK Elszámolás)"])
    st.markdown("---")
    
    st.header("⚙️ Műveletek")
    if st.button("🔁 Adatok beszippantása (Excelből)", type='primary', use_container_width=True):
        with st.spinner("Excels mappa tartalmának feldolgozása..."):
            success, msg = data_importer.process_and_import()
            if success:
                st.success(msg)
                time.sleep(2)
                st.rerun()
            else:
                st.error(msg)
                
    st.markdown("---")
    st.info("A nyers fájlokat (Kimenő számlák.xls, Elábé_lista.xls és alap_26.xlsx) az `Excels` mappában kell elhelyezni frissítés előtt.")

# --- Adat betöltése ---
df = get_data()

if df.empty:
    st.warning("Jelenleg nincs adat az adatbázisban. Kérjük használja az 'Adatok beszippantása' gombot.")
    st.stop()

if view_mode == "📊 Fő Dashboard":
    # --- Metrikák ---
    col1, col2, col3, col4 = st.columns(4)
    total_bevetel = df['SzumElad'].sum()
    total_res = df['Rés'].sum()
    total_jutalek = df['Jut'].sum()
    
    # Mennyi folyt be
    df_befolyt = df[df['Befolyt'] == 'i']
    sh_befolyt_arany = (len(df_befolyt) / len(df)) * 100 if len(df) > 0 else 0
    
    col1.metric("Összes Eladás (Ft)", f"{total_bevetel:,.0f}".replace(',', ' '))
    col2.metric("Teljes Rés (Ft)", f"{total_res:,.0f}".replace(',', ' '))
    col3.metric("Fizetendő Jutalék (Ft)", f"{total_jutalek:,.0f}".replace(',', ' '))
    col4.metric("Kifizetett számlák aránya", f"{sh_befolyt_arany:.1f}%")
    
    st.markdown("---")
    
    # Befolyt2 számítása
    def calc_befolyt2(row):
        uk = str(row['ÜK_kifizet_hó']).strip()
        is_empty = (uk == '' or uk.lower() == 'nan' or uk == 'None')
        if is_empty and row['Befolyt'] == 'n':
            return 'nem fizethető'
        elif row['Befolyt'] == 'i' and is_empty:
            return 'kifizethető'
        elif not is_empty:
            return 'fizetve'
        return ''
    
    df['Befolyt2'] = df.apply(calc_befolyt2, axis=1)
    
    # --- Szűrések ---
    st.subheader("🔍 Szűrés és Keresés")
    f_col1, f_col2, f_col3, f_col4, f_col5 = st.columns(5)
    with f_col1:
        uk_list = ['Mindenki'] + list(df['ÜK'].dropna().unique())
        sel_uk = st.selectbox("Üzletkötő", uk_list)
    with f_col2:
        vevo_list = ['Mind'] + list(df['Vevő'].dropna().unique())
        sel_vevo = st.selectbox("Vevő", vevo_list)
    with f_col3:
        sel_befolyt = st.radio("Fizetés állapota", ["Mind", "Befolyt ('i')", "Kintlévőség ('n')"], horizontal=True)
    with f_col4:
        tk_list = ['Mind'] + list(df['Termékkör'].dropna().unique())
        sel_tk = st.selectbox("Termékkör", tk_list)
    with f_col5:
        tf_list = ['Mind'] + list(df['Termékfajta'].dropna().unique())
        sel_tf = st.selectbox("Termékfajta", tf_list)
        
    # Szűrés alkalmazása
    filtered_df = df.copy()
    if sel_uk != 'Mindenki':
        filtered_df = filtered_df[filtered_df['ÜK'] == sel_uk]
    if sel_vevo != 'Mind':
        filtered_df = filtered_df[filtered_df['Vevő'] == sel_vevo]
    if sel_befolyt == "Befolyt ('i')":
        filtered_df = filtered_df[filtered_df['Befolyt'] == 'i']
    elif sel_befolyt == "Kintlévőség ('n')":
        filtered_df = filtered_df[filtered_df['Befolyt'] == 'n']
    if sel_tk != 'Mind':
        filtered_df = filtered_df[filtered_df['Termékkör'] == sel_tk]
    if sel_tf != 'Mind':
        filtered_df = filtered_df[filtered_df['Termékfajta'] == sel_tf]
        
    st.markdown(f"**Találatok száma: {len(filtered_df)} sor**")
    st.markdown("---")

    # --- Tömeges Kifizetési Hónap Feltöltés ---
    st.subheader("🗓️ Tömeges Kifizetési Hónap Feltöltés")
    # Kiszűrjük a JELENLEGES szűrésből amik befolytak (i), de nincs kifizetési hónap
    missing_ho_df = filtered_df[(filtered_df['Befolyt'] == 'i') & (filtered_df['ÜK_kifizet_hó'].isna() | (filtered_df['ÜK_kifizet_hó'] == '') | (filtered_df['ÜK_kifizet_hó'] == 'None'))]
    
    st.write(f"A fenti szűrés alapján **{len(missing_ho_df)} db** olyan tétel van jelenleg kiválasszva, amely már **befolyt**, de **még nincs megadva** hozzá kifizetési hónap.")
    
    if not missing_ho_df.empty:
        col_month, col_btn = st.columns([2, 8])
        with col_month:
            mass_month = st.number_input("Hónap (akár 13+ is):", step=1, value=1)
        with col_btn:
            st.write("") # Spacer
            st.write("") # Spacer
            if st.button("💾 Tömeges Feltöltés Mentése", type='primary'):
                database.mass_update_kifizet_ho(missing_ho_df['id'].tolist(), str(mass_month))
                st.success(f"{len(missing_ho_df)} tétel sikeresen frissítve a(z) {mass_month}. hónapra!")
                time.sleep(1)
                get_data.clear()
                st.rerun()

    st.markdown("---")

    # --- Adattábla szerkesztő ---
    st.subheader("📝 Adattábla és Egyedi Mező Szerkesztő")
    st.write("A **ÜK_kifizet_hó** és a **KülföldEUR** oszlopokat duplaklikkel szerkesztheted. A változások automatikusan mentődnek az adatbázisba.")
    
    # Formázó függvény a piros kiemeléshez
    def color_modified_jut(row):
        color = 'color: red; font-weight: bold' if row.get('Jut_modositott', 0) == 1 else ''
        return ['' if c not in ['Jut_%', 'Jut'] else color for c in row.index]

    # Formatálások a jobb olvashatóságért (nem visszamentődik, csak UI)
    view_df = filtered_df[['id', 'Szla', 'Cikk', 'Termékkör', 'Termékfajta', 'Vevő', 'Dátum', 'Megnevezés', 'SzumElad', 'Jut_%', 'Jut', 'Jut_modositott', 'Befolyt', 'Befolyt2', 'ÜK_kifizet_hó', 'KülföldEUR', 'ÜK']]
    
    # Alkalmazzuk a Stylert a fő táblázatra is
    styled_view_df = view_df.style.apply(color_modified_jut, axis=1)
    
    edited_df = st.data_editor(
        styled_view_df,
        disabled=['id', 'Szla', 'Cikk', 'Termékkör', 'Termékfajta', 'Vevő', 'Dátum', 'Megnevezés', 'SzumElad', 'Jut_%', 'Jut', 'Jut_modositott', 'ÜK', 'Befolyt', 'Befolyt2'], # Csak a kettő maradt szabad
        hide_index=True,
        use_container_width=True,
        key="data_editor",
    )
    
    # --- Módosítások mentése ---
    # Ha volt változtatás a st.session_state["data_editor"]["edited_rows"] -ban, elmentjük.
    if st.session_state.get("data_editor", {}).get("edited_rows"):
        changes = st.session_state["data_editor"]["edited_rows"]
        
        has_updates = False
        warning_shown = False
        
        for row_idx_str, mods in changes.items():
            row_idx = int(row_idx_str)
            
            real_id = view_df.iloc[row_idx]['id']
            
            curr_col = view_df.iloc[row_idx]['ÜK_kifizet_hó']
            curr_eur = view_df.iloc[row_idx]['KülföldEUR']
            curr_bef = view_df.iloc[row_idx]['Befolyt']
            
            new_col = mods.get('ÜK_kifizet_hó', curr_col)
            new_eur = mods.get('KülföldEUR', curr_eur)
            
            # Validáció: ha Befolyt == 'n', nem engedjük az ÜK_kifizet_hó módosítását nem üresre
            if curr_bef == 'n' and str(new_col).strip() != '' and str(new_col).lower() != 'nan' and new_col is not None:
                if not warning_shown:
                    st.warning("⚠️ Olyan sornál próbáltad megadni a fizetési hónapot, ami még nem folyt be (Befolyt = 'n'). A kifizetési hónap nem mentődött el ennél a sornál.")
                    warning_shown = True
                new_col = '' # Blank out the invalid edit
            
            if new_eur is not None and str(new_eur).strip() != '':
                try: new_eur = float(new_eur)
                except: new_eur = curr_eur
            
            database.update_custom_fields(real_id, str(new_col) if new_col is not None else None, new_eur)
            has_updates = True
            
        if has_updates:
            st.success("Cella módosítások az adatbázisban sikeresen elmentve!")
            get_data.clear() # Cache törlés hogy azonnal látszódjon a friss
            time.sleep(1)
            st.rerun()

    st.markdown("---")
    
    # --- Jutalék % Módosítása Fül ---
    st.subheader("💰 Egyedi Jutalék % Módosítása")
    st.write("Keresd meg a számlát aminek a tételein a beépített jutalék %-ot felül akarod írni.")
    
    szla_input = st.text_input("Írd be a módosítandó Számla számát (Szla):", placeholder="pl. 727 vagy 727/2026")
    
    # Ha más számlaszámot írtunk be, frissítjük a memóriában lévő modellt
    if 'szla_input_mem' not in st.session_state or st.session_state['szla_input_mem'] != szla_input:
        st.session_state['szla_input_mem'] = szla_input
        st.session_state['has_unsaved_changes'] = False
        
        if szla_input:
            szla_df = df[df['Szla'].astype(str).str.startswith(szla_input + '/') | (df['Szla'] == szla_input)]
            if not szla_df.empty:
                st.session_state['jut_view_mem'] = szla_df[['id', 'Cikk', 'Megnevezés', 'ÜK', 'SzumElad', 'Jut_%', 'Jut', 'Jut_modositott']].copy()
                st.session_state['szla_str_mem'] = szla_df.iloc[0]['Szla']
            else:
                st.session_state['jut_view_mem'] = None
        else:
            st.session_state['jut_view_mem'] = None
            
    if szla_input and st.session_state.get('jut_view_mem') is not None:
        szla_str = st.session_state['szla_str_mem']
        st.markdown(f"**Tételek a(z) {szla_str} számlához:**")
        
        editor_key = "jut_editor_mem_key"
        
        # Ez fut le amikor a user szerkeszt egy Jut_% vagy ÜK cellát
        def on_jut_change():
            if editor_key in st.session_state and "edited_rows" in st.session_state[editor_key]:
                edits = st.session_state[editor_key]["edited_rows"]
                mem_df = st.session_state['jut_view_mem']
                changed = False
                for row_idx_str, mods in edits.items():
                    row_idx = int(row_idx_str)
                    if 'ÜK' in mods:
                        mem_df.iat[row_idx, mem_df.columns.get_loc('ÜK')] = str(mods['ÜK'])
                        mem_df.iat[row_idx, mem_df.columns.get_loc('Jut_modositott')] = 1
                        changed = True
                    if 'Jut_%' in mods:
                        try:
                            # Ha üresre törlik, vegyük 0-nak
                            new_pct_str = mods['Jut_%']
                            new_pct = float(new_pct_str) if new_pct_str not in [None, ''] else 0.0
                            szum_elad = mem_df.iloc[row_idx]['SzumElad']
                            
                            mem_df.iat[row_idx, mem_df.columns.get_loc('Jut_%')] = new_pct
                            mem_df.iat[row_idx, mem_df.columns.get_loc('Jut')] = szum_elad * (new_pct / 100.0)
                            mem_df.iat[row_idx, mem_df.columns.get_loc('Jut_modositott')] = 1
                            changed = True
                        except ValueError:
                            pass
                if changed:
                    st.session_state['has_unsaved_changes'] = True

        styled_jut_view = st.session_state['jut_view_mem'].style.apply(color_modified_jut, axis=1)
        
        st.data_editor(
            styled_jut_view,
            disabled=['id', 'Cikk', 'Megnevezés', 'SzumElad', 'Jut', 'Jut_modositott'], # Csak a Jut_% és az ÜK szerkeszthető
            key=editor_key,
            hide_index=True,
            use_container_width=True,
            on_change=on_jut_change
        )
        
        # Mentés gomb
        if st.button("💾 Módosítások mentése az adatbázisba", type='primary'):
            if st.session_state.get('has_unsaved_changes', False):
                mem_df = st.session_state['jut_view_mem']
                has_jut_updates = False
                # Végigmegyünk, hogy miket modósított a felhasználó a session alatt
                for idx, row in mem_df.iterrows():
                    # Amelyiknél 1-es a modositott flag (lehet eleve is 1 volt, de updateeljük ha kell)
                    if row['Jut_modositott'] == 1:
                        database.update_jutalek_es_uk(row['id'], row['Jut_%'], row['Jut'], str(row['ÜK']))
                        has_jut_updates = True
                
                if has_jut_updates:
                    st.success("Jutalék átkalkulálva, adatbázisba mentve!")
                    get_data.clear()
                    st.session_state['szla_input_mem'] = None # Következő körben újrahúzza
                    st.session_state['has_unsaved_changes'] = False
                    time.sleep(1)
                    st.rerun()
            else:
                st.info("Nincs módosítás amit menteni kéne.")
    elif szla_input:
        st.warning("Nincs ilyen számlaszám az adatbázisban.")

    # --- További Kimutatások / Grafikonok ---
    st.subheader("📈 Havi aggregációk")
    if not filtered_df.empty and 'Kelt_hó' in filtered_df.columns:
        monthly = filtered_df.groupby('Kelt_hó')[['SzumElad', 'Rés']].sum().reset_index()
        monthly = monthly.rename(columns={'Kelt_hó': 'Hónap', 'SzumElad': 'Bevétel', 'Rés': 'Tiszta Rés'})
        st.bar_chart(monthly, x='Hónap', y=['Bevétel', 'Tiszta Rés'])
