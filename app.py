import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Institutional Terminal", layout="wide")
st.title("🛡️ US Kurumsal Akış & Opsiyon Radarı")

if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
    
    # SIDEBAR Sorgu
    st.sidebar.header("🔍 Hisse Derin Analiz")
    ticker = st.sidebar.text_input("Ticker:").upper()
    if ticker:
        h = df[df['ticker'] == ticker]
        if not h.empty:
            st.sidebar.metric("Quant Skor", h['quant_score'].iloc[0], f"{h['score_diff'].iloc[0]:+.2f}")
            st.sidebar.write(f"Opsiyon OI Momentum: %{h['pct_oi_mom'].iloc[0]:.0f}")
            st.sidebar.write(f"Skew (Put/Call) Rank: %{h['pct_skew'].iloc[0]:.0f}")

    # ANA TABLO
    st.subheader("🏆 Opsiyon ve Squeeze Onaylı Liderler")
    cols = ['ticker', 'quant_score', 'score_diff', 'pct_oi_mom', 'pct_skew', 'squeeze_skor', 'rvol_ratio']
    names = ['Hisse', 'Skor', 'Fark', 'Opsiyon OI %', 'Skew %', 'Squeeze', 'Hacim Z']
    
    st.dataframe(
        df.head(25)[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Skor'], cmap='YlGn'),
        use_container_width=True
    )
    
    st.caption("💡 **Opsiyon OI %:** Para girişini, **Skew %:** Boğa duyarlılığını temsil eder.")
else:
    st.info("Veri bekleniyor...")
