import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import database
import data_importer
import time
import plotly.express as px

# --- Oldal beállítások ---
st.set_page_config(page_title="H-ITB Elszámolás", layout="wide", initial_sidebar_state="collapsed")
st.title("📊 H-ITB Elszámolás Kezelő")

# Inicializálás
database.init_db()

# --- Függvény az adatok frissítéséhez az UI-ból ---
@st.cache_data(ttl=1) # Cache trükk hogy azonnal lássuk a módosítást
def get_data():
    return database.load_data_for_ui()

# --- Sidebar: Műveletek ---
with st.sidebar:
    st.header("🗂️ Nézet Választó")
    view_mode = st.radio("Válassz nézetet:", [
        "📊 Fő Dashboard", 
        "📑 1. Munkafolyamat (ÜK jutalék ellenőrzés)",
        "📈 2. Munkafolyamat (ÜK Elszámolás)",
        "💼 3. Munkafolyamat (ÜK KTGC)"
    ])
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

# --- Fő Dashboard ---
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
        if row.get('Resz_fizetett', 0) == 1:
            return 'Rész fizetett'
            
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
        filtered_df = filtered_df[(filtered_df['Befolyt'] == 'i') | (filtered_df['Resz_fizetett'] == 1)]
    elif sel_befolyt == "Kintlévőség ('n')":
        filtered_df = filtered_df[(filtered_df['Befolyt'] == 'n') & (filtered_df.get('Resz_fizetett', 0) != 1)]
    if sel_tk != 'Mind':
        filtered_df = filtered_df[filtered_df['Termékkör'] == sel_tk]
    if sel_tf != 'Mind':
        filtered_df = filtered_df[filtered_df['Termékfajta'] == sel_tf]
        
    st.markdown(f"**Találatok száma: {len(filtered_df)} sor**")
    st.markdown("---")

    # --- Tömeges Kifizetési Hónap Feltöltés ---
    st.subheader("🗓️ Tömeges Kifizetési Hónap Feltöltés")
    # Kiszűrjük a JELENLEGES szűrésből amik befolytak (i) VAGY részlet fizetve vannak (1), de nincs kifizetési hónap
    missing_ho_df = filtered_df[((filtered_df['Befolyt'] == 'i') | (filtered_df['Resz_fizetett'] == 1)) & (filtered_df['ÜK_kifizet_hó'].isna() | (filtered_df['ÜK_kifizet_hó'] == '') | (filtered_df['ÜK_kifizet_hó'] == 'None'))]
    
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
    view_df = filtered_df[['id', 'Szla', 'Vevő', 'Dátum', 'SzumBeker', 'SzumElad', 'Rés', 'ÜK', 'Jut_%', 'Jut', 'Befolyt', 'Befolyt2', 'Resz_fizetett', 'ÜK_kifizet_hó', 'Cikk', 'Termékkör', 'Termékfajta', 'Megnevezés', 'KülföldEUR', 'Jut_modositott']]
    
    # A Resz_fizetett oszlopot logikai típusra konvertáljuk a checkboxhoz
    view_df['Resz_fizetett'] = view_df['Resz_fizetett'].fillna(0).astype(bool)
    
    def format_editor_currency(val):
        if pd.isna(val): return ""
        if isinstance(val, (int, float)):
            return f"{val:,.0f} Ft".replace(',', ' ')
        return val

    def format_editor_percent(val):
        if pd.isna(val): return ""
        if isinstance(val, (int, float)):
            return f"{val:.2f}"
        return val

    # Alkalmazzuk a Stylert a fő táblázatra is
    styled_view_df = view_df.style.apply(color_modified_jut, axis=1).format({
        'SzumBeker': format_editor_currency,
        'SzumElad': format_editor_currency,
        'Rés': format_editor_currency,
        'Jut': format_editor_currency,
        'Jut_%': format_editor_percent
    })
    
    edited_df = st.data_editor(
        styled_view_df,
        column_config={
            "Resz_fizetett": st.column_config.CheckboxColumn(
                "Részlet (Skontó)",
                help="Pipáld be, ha a tétel részlegesen fizetve (skontó) lett, és így elszámolható jutalékra.",
                default=False,
            ),
            "Jut_modositott": None, # Elrejtjük az oszlopot a UI elől, mert pirossal jelezzük
        },

        disabled=['id', 'Szla', 'Cikk', 'Termékkör', 'Termékfajta', 'Vevő', 'Dátum', 'Megnevezés', 'SzumBeker', 'SzumElad', 'Rés', 'Jut_%', 'Jut', 'Jut_modositott', 'ÜK', 'Befolyt', 'Befolyt2'], # Resz_fizetett, ÜK_kifizet_hó, KülföldEUR szerkeszthető
        hide_index=True,
        use_container_width=True,
        key="data_editor",
    )
    
    # --- Excel Exportálás ---
    import io
    
    @st.cache_data(show_spinner=False)
    def convert_df_to_excel(df_to_export):
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df_to_export.to_excel(writer, index=False, sheet_name='Export')
        return output.getvalue()
        
    export_df = view_df.drop(columns=['Jut_modositott'], errors='ignore')
    excel_data = convert_df_to_excel(export_df)
    
    st.download_button(
        label="📥 Szűrt Táblázat Letöltése Excel-ként (.xlsx)",
        data=excel_data,
        file_name="Hitb_Elszamolas_Kivonat.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="export_btn"
    )
    
    # --- Módosítások mentése ---
    # Ha volt változtatás a st.session_state["data_editor"]["edited_rows"] -ban, elmentjük.
    if st.session_state.get("data_editor", {}).get("edited_rows"):
        changes = st.session_state["data_editor"]["edited_rows"]
        
        has_updates = False
        warning_shown = False
                    
        for row_idx_str, mods in changes.items():
            try:
                row_idx = int(row_idx_str) if str(view_df.index.dtype).startswith(('int', 'int64')) else row_idx_str
                real_id = int(view_df.loc[row_idx, 'id']) # KÖTELEZŐ natív int() a Numpy int64 SQLite inkompatibilitása miatt!
                curr_col = view_df.loc[row_idx, 'ÜK_kifizet_hó']
                curr_eur = view_df.loc[row_idx, 'KülföldEUR']
                curr_bef = view_df.loc[row_idx, 'Befolyt']
                curr_resz = view_df.loc[row_idx, 'Resz_fizetett']
            except KeyError:
                continue

            
            new_col = mods.get('ÜK_kifizet_hó', curr_col)
            new_eur = mods.get('KülföldEUR', curr_eur)
            new_resz = mods.get('Resz_fizetett', None)
            if new_resz is not None:
                database.update_resz_fizetett(real_id, 1 if new_resz else 0)
                has_updates = True
            
            # Validáció: ha Befolyt == 'n' ÉS nem 'Rész fizetett', nem engedjük az ÜK_kifizet_hó módosítását nem üresre
            is_resz_fizetett = (new_resz == True) if new_resz is not None else (curr_resz == True)
            if curr_bef == 'n' and not is_resz_fizetett and str(new_col).strip() != '' and str(new_col).lower() != 'nan' and new_col is not None:
                if not warning_shown:
                    st.warning("⚠️ Olyan sornál próbáltad megadni a fizetési hónapot, ami nincs fizetve (Befolyt = 'n'). A kifizetési hónap nem mentődött el ennél a sornál.")
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
            
            # Törölni kell a "data_editor" kulcsot a session_state-ből, hogy megelőzzünk egy végtelen frissítési ciklust
            if "data_editor" in st.session_state:
                del st.session_state["data_editor"]
                
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

    # --- SzumBeker és Pivot Kimutatások / Grafikonok ---
    if not df.empty and 'Kelt_hó' in df.columns:
        pdf_full = df.copy()
        
        # Opcionális Hónap Szűrő
        available_months = sorted([m for m in pdf_full['Kelt_hó'].unique() if pd.notnull(m)])
        month_options = ["Összes"] + [str(int(m)) + ". hónap" for m in available_months]
        selected_month_str = st.selectbox("Szűrés Dátum (Hónap) szerint:", month_options)
        
        if selected_month_str != "Összes":
            sel_m = int(selected_month_str.split('.')[0])
            pdf = pdf_full[pdf_full['Kelt_hó'] == sel_m].copy()
        else:
            pdf = pdf_full.copy()
            
        if not pdf.empty:
            # A felhasználó logikája: a "Főcsoport" az valójában a Termékfajta (Alap, Beruházás)
            # Az "Alcsoport" pedig a Termékkör (Acélsodronyok, stb.)
            pdf.loc[:, 'Főcsoport'] = pdf['Termékfajta'].replace(['', None], 'Ismeretlen').fillna('Ismeretlen')
            pdf.loc[:, 'Alcsoport'] = pdf['Termékkör'].replace(['', None], 'Ismeretlen').fillna('Ismeretlen')
            
            # Az Excel pivot táblázatában az Árrés egy Calculated Field: Rés - Jutalék
            pdf['Árrés_számított'] = pdf['Rés'].fillna(0) - pdf['Jut'].fillna(0)

        
            # Közös formázó függvények mindkét táblázathoz
            def highlight_pivot(row):
                idx = str(row.name).replace('\u200B', '') if hasattr(row, 'name') else ''
                # DataFrame apply esetében name az index; de ha oszlopban tartjuk, lekezeljük:
                if 'Sum of Árrés' in row: idx = str(row['Sum of Árrés']).replace('\u200B', '')
                elif 'Sum of SzumElad' in row: idx = str(row.get('Sum of SzumElad', '')).replace('\u200B', '')
                
                if idx == "Grand Total":
                    return ['background-color: #d4edda; color: #155724; font-weight: bold !important;'] * len(row)
                elif "összesen" in idx:
                    return ['background-color: #FAFAFA; color: #0E1117; font-weight: bold !important;'] * len(row)
                else:
                    return [''] * len(row)

            def format_currency(val):
                if pd.isna(val): return ""
                if isinstance(val, (int, float)):
                    return f"{val:,.0f} Ft".replace(',', ' ')
                return val

            # ==========================================
            # 1. SZUMELAD SZEKCIÓ (TÁBLÁZAT + DIAGRAM)
            # ==========================================
            st.subheader("🛒 Termékkörök és SzumElad")
            
            pivot_main_elad = pd.pivot_table(
                pdf, values='SzumElad', index='Főcsoport', columns='Kelt_hó',
                aggfunc='sum', fill_value=0, margins=True, margins_name='Grand Total'
            )
            
            pivot_detail_elad = pd.pivot_table(
                pdf, values='SzumElad', index=['Főcsoport', 'Alcsoport'], columns='Kelt_hó',
                aggfunc='sum', fill_value=0, margins=True, margins_name='Grand Total'
            )
            
            rows_elad = []
            for focsoport, row in pivot_main_elad.iterrows():
                if focsoport == 'Grand Total':
                    continue
                r = row.to_dict()
                r['Sum of SzumElad'] = f"🔹 {focsoport} összesen"
                rows_elad.append(r)
                
                for (m_fo, m_al), d_row in pivot_detail_elad.iterrows():
                    if m_fo == focsoport and m_fo != 'Grand Total':
                        dr = d_row.to_dict()
                        dr['Sum of SzumElad'] = f"    {m_al}"
                        rows_elad.append(dr)
                        
            if 'Grand Total' in pivot_main_elad.index:
                gt_e = pivot_main_elad.loc['Grand Total'].to_dict()
                gt_e['Sum of SzumElad'] = "Grand Total"
                rows_elad.append(gt_e)
                
            final_elad_df = pd.DataFrame(rows_elad)
            if not final_elad_df.empty:
                counts_e = {}
                new_names_e = []
                for name in final_elad_df['Sum of SzumElad']:
                    new_names_e.append(name + ('\u200B' * counts_e.get(name, 0)))
                    counts_e[name] = counts_e.get(name, 0) + 1
                final_elad_df['Sum of SzumElad'] = new_names_e
                
                final_elad_df = final_elad_df.set_index('Sum of SzumElad')
                final_elad_df = final_elad_df.fillna(0).round(0).astype(int)
                
                new_cols_e = []
                for col in final_elad_df.columns:
                    if col == 'Grand Total':
                        new_cols_e.append(col)
                    else:
                        try: new_cols_e.append(str(int(float(col))))
                        except: new_cols_e.append(str(col))
                final_elad_df.columns = new_cols_e
                
                styled_elad = final_elad_df.style.apply(highlight_pivot, axis=1).format(format_currency)
                st.dataframe(styled_elad, use_container_width=True)
            else:
                st.info("Nincs megjeleníthető SzumElad adat a táblázathoz.")

            st.subheader("📈 SzumElad megoszlása (Főcsoportonként)")
            chart_df_elad = pdf.groupby(['Kelt_hó', 'Főcsoport'])['SzumElad'].sum().reset_index()
            chart_df_elad['Kelt_hó'] = chart_df_elad['Kelt_hó'].astype(str) + ". hónap"
            fig_elad = px.bar(
                chart_df_elad, x='Kelt_hó', y='SzumElad', color='Főcsoport', 
                title='Havi SzumElad Termékfajtánkénti (Főcsoport) bontásban', text_auto='.2s'
            )
            st.plotly_chart(fig_elad, use_container_width=True)


            # Elválasztó
            st.markdown("---")


            # ==========================================
            # 2. ÁRRÉS SZEKCIÓ (TÁBLÁZAT + DIAGRAM)
            # ==========================================
            st.subheader("📊 Termékkörök és Árrés")
            
            # Főcsoport Pivot
            pivot_main = pd.pivot_table(
                pdf, values='Árrés_számított', index='Főcsoport', columns='Kelt_hó',
                aggfunc='sum', fill_value=0, margins=True, margins_name='Grand Total'
            )
            
            # Alcsoport Pivot
            pivot_detail = pd.pivot_table(
                pdf, values='Árrés_számított', index=['Főcsoport', 'Alcsoport'], columns='Kelt_hó',
                aggfunc='sum', fill_value=0, margins=True, margins_name='Grand Total'
            )
            
            rows = []
            for focsoport, row in pivot_main.iterrows():
                if focsoport == 'Grand Total':
                    continue
                r = row.to_dict()
                r['Sum of Árrés'] = f"🔹 {focsoport} összesen"
                rows.append(r)
                
                for (m_fo, m_al), d_row in pivot_detail.iterrows():
                    if m_fo == focsoport and m_fo != 'Grand Total':
                        dr = d_row.to_dict()
                        dr['Sum of Árrés'] = f"    {m_al}"
                        rows.append(dr)
                        
            if 'Grand Total' in pivot_main.index:
                gt = pivot_main.loc['Grand Total'].to_dict()
                gt['Sum of Árrés'] = "Grand Total"
                rows.append(gt)
                
            final_pivot_df = pd.DataFrame(rows)
            if not final_pivot_df.empty:
                counts = {}
                new_names = []
                for name in final_pivot_df['Sum of Árrés']:
                    new_names.append(name + ('\u200B' * counts.get(name, 0)))
                    counts[name] = counts.get(name, 0) + 1
                final_pivot_df['Sum of Árrés'] = new_names
                
                final_pivot_df = final_pivot_df.set_index('Sum of Árrés')
                final_pivot_df = final_pivot_df.fillna(0).round(0).astype(int)
                
                new_columns = []
                for col in final_pivot_df.columns:
                    if col == 'Grand Total':
                        new_columns.append(col)
                    else:
                        try:
                            new_columns.append(str(int(float(col))))
                        except:
                            new_columns.append(str(col))
                final_pivot_df.columns = new_columns
                
                styled_pivot = final_pivot_df.style.apply(highlight_pivot, axis=1).format(format_currency)
                st.dataframe(styled_pivot, use_container_width=True)
            else:
                st.info("Nincs megjeleníthető Árrés adat a táblázathoz.")

            st.subheader("📈 Árrés megoszlása (Főcsoportonként)")
            chart_df = pdf.groupby(['Kelt_hó', 'Főcsoport'])['Árrés_számított'].sum().reset_index()
            chart_df['Kelt_hó'] = chart_df['Kelt_hó'].astype(str) + ". hónap"
            fig = px.bar(
                chart_df, x='Kelt_hó', y='Árrés_számított', color='Főcsoport', 
                title='Havi Árrés Termékfajtánkénti (Főcsoport) bontásban', text_auto='.2s'
            )
            st.plotly_chart(fig, use_container_width=True)

        else:
            st.info("Nincs megjeleníthető adat az adott formátumhoz a kiválasztott szűrés alapján.")

    st.markdown("---")
    
    # --- Üzletkötői céglista vásárlás szerint ---
    st.subheader("🏢 Üzletkötői Céglista Vásárlás Szerint")
    st.write("Az alábbi lista az üzletkötők cégeit mutatja vásárlási forgalom szerinti csökkenő sorrendben. *(Az adatok az oldal tetején lévő szűrők alapján frissülnek.)*")
    
    if not filtered_df.empty:
        uk_vevo_df = filtered_df.groupby(['ÜK', 'Vevő'])['SzumElad'].sum().reset_index()
        uks = sorted([uk for uk in uk_vevo_df['ÜK'].dropna().unique() if str(uk).strip() != ''])
        
        export_vevo_df = uk_vevo_df.sort_values(by=['ÜK', 'SzumElad'], ascending=[True, False]).reset_index(drop=True)
        export_vevo_df = export_vevo_df.rename(columns={'Vevő': 'Cégnév', 'SzumElad': 'Összes Vásárlás (Ft)'})
        
        st.write("")
        st.download_button(
            label="📥 Üzletkötői Lista Letöltése Excel-ként",
            data=convert_df_to_excel(export_vevo_df),
            file_name="ÜK_Vásárlói_Toplista.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="export_vevo_btn"
        )
        st.write("")
        
        if len(uks) > 0:
            tabs = st.tabs(uks)
            for index, uk in enumerate(uks):
                with tabs[index]:
                    uk_data = uk_vevo_df[uk_vevo_df['ÜK'] == uk].sort_values(by='SzumElad', ascending=False).reset_index(drop=True)
                    uk_data = uk_data.rename(columns={'Vevő': 'Cégnév', 'SzumElad': 'Összes Vásárlás (Ft)'})
                    uk_data.index = uk_data.index + 1
                    
                    st.dataframe(
                        uk_data[['Cégnév', 'Összes Vásárlás (Ft)']].style.format({'Összes Vásárlás (Ft)': '{:,.0f} Ft'.format}),
                        use_container_width=True
                    )
        else:
            st.info("Nincs megjeleníthető üzletkötői adat a jelenlegi szűréssel.")

elif view_mode in ["📑 1. Munkafolyamat (ÜK jutalék ellenőrzés)", "📈 2. Munkafolyamat (ÜK Elszámolás)"]:
    title = "📑 1. Munkafolyamat: ÜK jutalék ellenőrzés" if "1. Munkafolyamat" in view_mode else "📈 2. Munkafolyamat: ÜK Elszámolás"
    st.title(title)
    
    # Közös logika mindkét folyamathoz:
    # Kelt_hó kiválasztása csak az 1. munkafolyamatnál
    if "1. Munkafolyamat" in view_mode:
        avail_months = sorted(df['Kelt_hó'].dropna().unique())
        selected_ho = st.selectbox("Válassz hónapot (Kelt_hó):", avail_months)
    else:
        selected_ho = None
        st.info("💡 Ez a nézet az összes hónap kifizetetlen, de már befolyt jutalékait mutatja meg ömlesztve, így nincs havi szűrő.")
    
    # ÜK lista és aktiváció
    st.subheader("Üzletkötők kiválasztása")
    all_uks = sorted(df['ÜK'].dropna().unique())
    active_uks = database.get_active_uks()
    active_uks_initialized = active_uks is not None
    if not active_uks_initialized:
        active_uks = all_uks
        
    selected_uks = []
    cols = st.columns(4)
    for i, uk in enumerate(all_uks):
        default_val = (uk in active_uks)
        is_checked = cols[i % 4].checkbox(uk, value=default_val, key=f"uk_{uk}")
        if is_checked:
            selected_uks.append(uk)
            
    # Save if changed
    if set(selected_uks) != set(active_uks) or not active_uks_initialized:
        database.set_active_uks(selected_uks, all_uks)
        
    if st.button("📄 Lista Generálása", type="primary"):
        st.markdown("---")
        
        # --- Nyomtatási CSS ---
        st.markdown("""
        <style>
        @media print {
            @page {
                margin: 0.5cm;
                size: portrait; /* Kényszerített álló tájolás (Portrait) */
            }
            /* Oldalsáv, fejléc elrejtése */
            [data-testid="stSidebar"], [data-testid="stHeader"] { display: none !important; }
            
            /* Címsor kivételek: A generált uk-header maradhat csak (ha önmagában hívódnak is elrejtjük a többit) */
            h1, h2, h3:not(.uk-header), h4, h5, h6 { display: none !important; }
            
            /* Felesleges specifikus űrlapelemek elrejtése - Biztosítás gyanánt */
            .stButton, .stSelectbox, .stCheckbox, [data-testid="stRadio"], [data-testid="column"], hr, .no-print { display: none !important; }
            
            /* Kísértetként megmaradt, láthatatlan grafikon eszköztárak, tooltipek és SVG-k teljes blokkolása a nyomtatásról! */
            #vg-tooltip-element, .vg-tooltip, canvas, svg, iframe { display: none !important; }
            
            /* --- A NAGY ÜRES HELY ELTÜNTETÉSÉNEK TITKA --- */
            /* Zseniális trükk: Elrejtünk MINDEN konténert a tartalomban az első név előtt! */
            [data-testid="stVerticalBlock"] > .element-container { display: none !important; }
            [data-testid="stVerticalBlock"] > .element-container:has(.uk-header),
            [data-testid="stVerticalBlock"] > .element-container:has(.uk-header) ~ .element-container {
                display: block !important;
            }
            
            /* Címsorként funkcionáló szöveg div leleplezése Streamlitben */
            .stMarkdown div p { margin: 0; }
            
            /* MOST JÖN A LÉNYEG! A Streamlit konténereket NEM kényszerítjük fix (asztali/desktop) 100% szélességre (ami pl 1400px is lehet és ezért kilóg), 
               hanem ráeresztjük a nyomtató (PDF motor) "auto" méretezését, hogy belezsugorítsa magát az A4 lap szigorú 100%-ába (~700px)! */
            .main, .block-container, [data-testid="stAppViewBlockContainer"], .element-container, .stMarkdown {
                width: auto !important;
                max-width: 100vw !important; /* Ne szűkítsen a belső tartalom felé */
                min-width: 0 !important;
                padding: 0 !important;
                margin: 0 !important;
                overflow: visible !important; /* Hagyjuk a táblázatot kiférni a vágósíkból! */
            }
        }
        </style>
        """, unsafe_allow_html=True)
        
        # --- Dedikált HTML Nyomtatás Gomb ---
        components.html(
            """
            <div style="text-align: right;" class="no-print">
                <button onclick="window.parent.print()" style="
                    background-color: #4CAF50; border: none; color: white;
                    padding: 10px 24px; text-align: center; font-size: 16px;
                    cursor: pointer; border-radius: 8px; font-weight: bold;
                    font-family: sans-serif; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    transition: 0.3s;
                " onmouseover="this.style.backgroundColor='#45a049'" onmouseout="this.style.backgroundColor='#4CAF50'">
                🖨️ Nyomtatás
                </button>
            </div>
            """, height=60
        )
        
        if "1. Munkafolyamat" in view_mode:
            ho_df = df[df['Kelt_hó'] == selected_ho]
        else:
            ho_df = df.copy()
        
        # 2. Munkafolyamat szűrő feltételek!
        if "2. Munkafolyamat" in view_mode:
            # Csak ha be van folyva (i) VAGY részlet fizetve (1) ÉS az ÜK_kifizet_hó üres (null, üres sztring, NaN)
            ho_df = ho_df[ ((ho_df['Befolyt'] == 'i') | (ho_df['Resz_fizetett'] == 1)) & (ho_df['ÜK_kifizet_hó'].isnull() | (ho_df['ÜK_kifizet_hó'] == '') | (ho_df['ÜK_kifizet_hó'] == 'None') ) ]
            
        is_first = True
        for uk in selected_uks:
            if not is_first:
                st.markdown("<div style='page-break-before: always'></div>", unsafe_allow_html=True)
            is_first = False
            
            uk_safe_id = "".join(c if c.isalnum() else "_" for c in uk)
            
            if "2. Munkafolyamat" in view_mode:
                from datetime import datetime
                curr_date = datetime.now().strftime("%Y.%m.%d.")
                h3_html = f"""
                <h3 class='uk-header' style='margin-bottom: 5px; margin-top: 15px;'>
                    👤 <span contenteditable='true' 
                             class="uk-editable-{uk_safe_id}"
                             style="border-bottom: 1px dashed gray; outline: none;"
                             title="Kattints ide az Üzletkötő nevének átmeneti átírásához a nyomtatáshoz!"
                             >{uk}</span>
                    <span style='font-size: 0.8em; color: #555;'> - jutalék elszámolása {curr_date}</span>
                </h3>
                """
                st.markdown(h3_html, unsafe_allow_html=True)
            else:
                st.markdown(f"<h3 class='uk-header' style='margin-bottom: 5px; margin-top: 15px;'>👤 {uk}</h3>", unsafe_allow_html=True)
            
            uk_df = ho_df[ho_df['ÜK'] == uk]
            
            if uk_df.empty:
                st.info("Ebben a hónapban nincs adata.")
                continue
                
            res_df = pd.DataFrame()
            res_df['Befolyt'] = uk_df['Befolyt']
            res_df['ÜK'] = uk_df['ÜK']
            res_df['Szlasz.'] = uk_df['Szla']
            res_df['HÓ'] = uk_df['Kelt_hó']
            res_df['Vnév'] = uk_df['Vevő']
            res_df['TKÖRÖK'] = uk_df['Termékkör']
            res_df['FIZET'] = uk_df['SzumElad']
            res_df['JUT_%'] = uk_df['Jut_%']
            res_df['JUT'] = uk_df['Jut']
            res_df['JUT_fiz'] = uk_df['ÜK_kifizet_hó'].fillna('')
            
            # === HTML Táblázat kigenerálása a nyomtatáshoz ===
            def fmt_num(val): return f"{val:,.0f}".replace(',', ' ') + ' Ft'
            def fmt_pct(val): return f"{val:.2f}%"
            def fmt_ho(val): return f"{val:.0f}" if pd.notnull(val) and val != '' else ''
            
            # CSS kifejezetten a táblázatok szép nyomtatásához
            st.markdown("""
            <style>
            .print-table {
                width: 100% !important;
                table-layout: fixed !important; /* Fixálja az oszlopszélességeket az adott %-okon! Semmi sem nyomhatja szét. */
                border-collapse: collapse;
                font-size: 11.5px; /* Visszaállítva a korábbi, kényelmesebb méret, mivel a konténer most zsugorodik be! */
                font-family: sans-serif;
                margin-bottom: 20px;
                background-color: white !important;
                color: black !important;
            }
            .print-table th, .print-table td {
                border: 1px solid #777;
                padding: 3px 2px; /* Visszaállított normál cellamargók */
                text-align: left;
                color: black !important;
            }
            .print-table th {
                background-color: #e6e6e6 !important;
                font-weight: bold;
                text-align: center;
                overflow: hidden;
            }
            
            /* Szigorú oszlopszélességek a teljes álló lapszélesség felosztására (Összesen: 100%) */
            /* Levágjuk a túl hosszú vevőneveket a három ponttal (text-overflow: ellipsis) */
            .col-befolyt { width: 4%; text-align: center !important; }
            .col-uk      { width: 8%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .col-szlasz  { width: 9%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .col-ho      { width: 4%; text-align: center !important; }
            .col-vnev    { width: 22%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .col-tkorok  { width: 14%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .col-num     { width: 11%; text-align: right !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .col-jutpct  { width: 6%; text-align: right !important; }
            .col-jut     { width: 11%; text-align: right !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            .col-jutfiz  { width: 11%; text-align: right !important; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
            
            @media print {
                /* A nyomtatási globális beállításokat feljebb (a gomb megnyomásakor) definiáltuk,
                   hogy ne generálódjanak le minden egyes Üzletkötő táblázatánál újra! */
            }
            </style>
            """, unsafe_allow_html=True)
            
            html = "<table class='print-table'>"
            html += "<thead><tr>"
            html += "<th class='col-befolyt'>Befolyt</th>"
            html += "<th class='col-uk'>ÜK</th>"
            html += "<th class='col-szlasz'>Szlasz.</th>"
            html += "<th class='col-ho'>HÓ</th>"
            html += "<th class='col-vnev'>Vnév</th>"
            html += "<th class='col-tkorok'>TKÖRÖK</th>"
            html += "<th class='col-num'>FIZET</th>"
            html += "<th class='col-jutpct'>JUT_%</th>"
            html += "<th class='col-jut'>JUT</th>"
            html += "<th class='col-jutfiz'>JUT_fiz</th>"
            html += "</tr></thead><tbody>"
            
            for _, r in res_df.iterrows():
                html += "<tr>"
                html += f"<td class='col-befolyt'>{r['Befolyt']}</td>"
                html += f"<td class='col-uk uk-cell-{uk_safe_id}'>{r['ÜK']}</td>"
                html += f"<td class='col-szlasz'>{r['Szlasz.']}</td>"
                html += f"<td class='col-ho'>{fmt_ho(r['HÓ'])}</td>"
                html += f"<td class='col-vnev'>{r['Vnév']}</td>"
                html += f"<td class='col-tkorok'>{r['TKÖRÖK']}</td>"
                html += f"<td class='col-num'>{fmt_num(r['FIZET'])}</td>"
                html += f"<td class='col-jutpct'>{fmt_pct(r['JUT_%'])}</td>"
                html += f"<td class='col-jut'>{fmt_num(r['JUT'])}</td>"
                html += f"<td class='col-jutfiz'>{r['JUT_fiz']}</td>"
                html += "</tr>"
            
            html += "</tbody></table>"
            st.markdown(html, unsafe_allow_html=True)
            
            sum_fizet = res_df['FIZET'].sum()
            sum_jut = res_df['JUT'].sum()
            
            st.markdown(f"**Összes FIZET:** `{sum_fizet:,.0f} Ft` &nbsp;&nbsp;|&nbsp;&nbsp; **Összes JUT:** `{sum_jut:,.0f} Ft`")
            st.write("")
        
        # --- JavaScript Bűvölet a DOMPurify kicselezésére ---
        if "2. Munkafolyamat" in view_mode:
            components.html(
                """
                <script>
                // A Streamlit iframe-jéből "kinyúlunk" a szülő (fő) DOM-ba
                const doc = window.parent.document;
                
                // Keressük meg a szerkeszthető span-eket
                const editables = doc.querySelectorAll('span[class*="uk-editable-"]');
                
                editables.forEach(el => {
                    // Kinyerjük az azonosítót a class nevéből (pl. uk-editable-KissPista)
                    const uk_class = Array.from(el.classList).find(c => c.startsWith('uk-editable-'));
                    if (uk_class) {
                        const safe_id = uk_class.replace('uk-editable-', '');
                        
                        // Ráakasztjuk az eseményfigyelőt
                        el.addEventListener('input', function() {
                            const newText = this.innerText;
                            const cells = doc.querySelectorAll('.uk-cell-' + safe_id);
                            cells.forEach(c => c.innerText = newText);
                        });
                    }
                });
                </script>
                """, height=0
            )

elif view_mode == "💼 3. Munkafolyamat (ÜK KTGC)":
    st.title("💼 3. Munkafolyamat: ÜK KTGC Bónusz Paraméterek")
    
    active_uks = database.get_active_uks()
    if not active_uks:
        st.warning("Nincs aktív üzletkötő kiválasztva. Kérlek, előbb válaszd ki őket az '1. Munkafolyamat' nézetben!")
    else:
        with st.expander("🔽 Add meg az üzletkötőnkénti KTGC sarokszámokat (A változtatások automatikusan mentésre kerülnek)", expanded=False):
            # Callback függvény az adatok mentésére az on_change eseményeken
            def save_uk_settings(uk_name):
                def parse_val(key):
                    val = st.session_state.get(key, "0")
                    if isinstance(val, str):
                        val = val.replace('Ft', '').replace(' ', '').replace(',', '').strip()
                    try:
                        return float(val) if val else 0.0
                    except ValueError:
                        return 0.0
                        
                ossz_terv = parse_val(f'ossz_terv_{uk_name}')
                alap_terv = parse_val(f'alap_terv_{uk_name}')
                beruh_terv = parse_val(f'beruh_terv_{uk_name}')
                alap_limit = parse_val(f'alap_lim_{uk_name}')
                bonusz_limit = parse_val(f'bonusz_lim_{uk_name}')
                
                database.save_ktgc_settings(uk_name, {
                    'ossz_terv': ossz_terv,
                    'alap_terv': alap_terv,
                    'beruhazas_terv': beruh_terv,
                    'alap_limit': alap_limit,
                    'bonusz_limit': bonusz_limit
                })
                
            def fmt_money(val) -> str:
                try:
                    return f"{float(val):,.0f}".replace(',', ' ') + " Ft"
                except:
                    return "0 Ft"
            
            for uk in active_uks:
                with st.container(border=True):
                    st.subheader(f"👤 {uk}")
                    settings = database.get_ktgc_settings(uk)
                    
                    c1, c2, c3, c4 = st.columns(4)
                    
                    with c1:
                        st.text_input("Összforgalmi terv", value=fmt_money(settings['ossz_terv']), key=f"ossz_terv_{uk}", on_change=save_uk_settings, args=(uk,))
                    with c2:
                        ossz_val = settings['ossz_terv']
                        # Ha a session_state-ben már van új valid érték, azt használjuk
                        if f"ossz_terv_{uk}" in st.session_state:
                            val = st.session_state[f"ossz_terv_{uk}"]
                            if isinstance(val, str):
                                val = val.replace('Ft', '').replace(' ', '').replace(',', '').strip()
                            try:
                                ossz_val = float(val) if val else 0.0
                            except ValueError:
                                ossz_val = settings['ossz_terv']
                        
                        min_terv = ossz_val * 0.9
                        min_f = f"{min_terv:,.0f}".replace(',', ' ') + " Ft"
                        st.text_input("Min. terv (Összforg. 90%)", value=min_f, disabled=True, key=f"min_terv_{uk}")
                    with c3:
                        st.text_input("Alap terv", value=fmt_money(settings['alap_terv']), key=f"alap_terv_{uk}", on_change=save_uk_settings, args=(uk,))
                    with c4:
                        st.text_input("Beruházás terv", value=fmt_money(settings['beruhazas_terv']), key=f"beruh_terv_{uk}", on_change=save_uk_settings, args=(uk,))
                        
                    c5, c6, c7, c8 = st.columns(4)
                    with c5:
                        st.text_input("Alap limit", value=fmt_money(settings['alap_limit']), key=f"alap_lim_{uk}", on_change=save_uk_settings, args=(uk,))
                    with c6:
                        st.text_input("Bónusz limit", value=fmt_money(settings['bonusz_limit']), key=f"bonusz_lim_{uk}", on_change=save_uk_settings, args=(uk,))
