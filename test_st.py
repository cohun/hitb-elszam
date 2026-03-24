import streamlit as st
import pandas as pd

df = pd.DataFrame({'id': [100, 101, 102], 'Value': ['A', 'B', 'C']})
# Modify index
df.index = [15, 20, 25]

edited = st.data_editor(df, hide_index=True, key="ed")
st.write(st.session_state["ed"])
