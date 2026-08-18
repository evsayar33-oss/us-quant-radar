import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Quant Terminal", layout="wide")
st.title("📊 US Adaptive Quant Radar")
st.caption("Piyasa Duyarlılığını Dinamik Yüzdelik Dilimlerle Ölçer")

if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
    
    for col in ['quant_score', 'score_diff', 'pct_pc_rank']:
        if col in df.columns: df[col] = df[col].round(2)

    # SIDEBAR
    st.sidebar.header("🔍 Hisse Trend Analizi")
    search = st.sidebar.text_input("Hisse Kodu:").upper()
    if search:
        h = df[df['ticker'] == search]
        if not h.empty:
            st.sidebar.metric("Quant Skor", h['quant_score'].iloc[0], f"{h['score_diff'].iloc[0]:+.2f}")
            st.sidebar.write(f"**Opsiyon Gücü:** %{h['pct_pc_rank'].iloc[0]}")
            st.sidebar.caption("*(100'e yakınsa rakiplerinden daha boğa demektir)*")

    # TABLOLAR
    cols = ['ticker', 'quant_score', 'score_diff', 'pct_pc_rank', 'rvol_ratio', 'yapisal_skor']
    names = ['Hisse', 'Skor', 'Fark', 'Opsiyon Gücü %', 'RVOL', 'Yapısal']

    st.subheader("🏆 Günün Adaptif Liderleri")
    st.dataframe(df.head(20)[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Skor'], cmap='RdYlGn'), use_container_width=True)
    
    st.caption("💡 **Opsiyon Gücü %:** Bu hissenin opsiyon duyarlılığının piyasadaki diğer 250 hisseye göre ne kadar pozitif olduğunu gösterir. Sabit eşik kullanmaz, her gün kendini kalibre eder.")
else:
    st.info("Veri bekleniyor...")
