with open("app.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

out = []
for i, line in enumerate(lines):
    # Sidebar
    if line.strip() == 'st.header("⚙️ Műveletek")':
        out.append('    st.header("��️ Nézet Választó")\n')
        out.append('    view_mode = st.radio("Válassz nézetet:", ["📊 Fő Dashboard", "📑 1. Munkafolyamat (ÜK Elszámolás)"])\n')
        out.append('    st.markdown("---")\n')
        out.append('    \n')
        out.append('    st.header("⚙️ Műveletek")\n')
        continue
    
    # Adat betöltése és else blokk
    if line.strip() == '# --- Fő Dashboard ---':
        out.append('# --- Adat betöltése ---\n')
        continue
        
    if line.strip() == 'else:':
        if "warning" in lines[i-1]:
            out.append('    st.stop()\n\n')
            out.append('if view_mode == "📊 Fő Dashboard":\n')
            continue
            
    # Remove 1 level of indentation ONLY for lines inside the else block (lines 41-264 originally) if I decided to unindent
    # BUT wait, if I put `if view_mode == ...`, I DO need the indentation!
    # So actually, `else:` can just be replaced with `elif view_mode == "📊 Fő Dashboard":` !
    # Oh! `if df.empty:` -> `elif view_mode == ...` is a syntax error, because `if` needs an `else` or I can just change `if df.empty` to have `st.stop()`, then `if view_mode == "Fő Dashboard":`. If so, I DO need to unindent OR I just replace `else:` with `if view_mode == "📊 Fő Dashboard":` AND I ADD `st.stop()` inside `if df.empty:` ! Wait, if I add `st.stop()`, I can just change `else:` to `if view_mode == "...":` but keep the same indentation! Because python allows it. No, python doesn't allow random indent!
    
    out.append(line)

with open("app_new.py", "w", encoding="utf-8") as f:
    f.writelines(out)

