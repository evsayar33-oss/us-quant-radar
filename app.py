import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Quant Terminal", layout="wide")
st.title("🇺🇸 US Quant Nicel Radar & Çıkış Sistemi")

if os.path.exists("sonuclar.csv") and os.path.exists("gecmis_veri.csv"):
    df = pd.read_csv("sonuclar.csv")
    
    for col in ['quant_score', 'score_diff', 'pct_pc_rank']:
        if col in df.columns: df[col] = df[col].round(2)

    # SIDEBAR: Hisse Sorgulama
    st.sidebar.header("🔍 US Hisse Takip")
    search_ticker = st.sidebar.text_input("Hisse Kodu (Örn: NVDA):").upper()
    if search_ticker:
        h_data = df[df['ticker'] == search_ticker]
        if not h_data.empty:
            score = h_data['quant_score'].iloc[0]
            diff = h_data['score_diff'].iloc[0]
            status = "GÜÇLÜ" if score > 70 else "ZAYIF"
            st.sidebar.metric(f"{search_ticker} Skor", score, f"{diff:+.2f}")
            st.sidebar.write(f"**Durum:** {status}")
        else:
            st.sidebar.warning("Hisse bulunamadı.")

    # ANA TABLOLAR
    cols = ['ticker', 'quant_score', 'score_diff', 'pct_pc_rank', 'rvol_ratio', 'yapisal_skor']
    names = ['Hisse', 'Skor', 'Fark', 'Opsiyon %', 'RVOL', 'Yapısal']

    st.subheader("🏆 US Quant Liderleri (Top 20)")
    st.dataframe(df.head(20)[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Skor'], cmap='RdYlGn'), use_container_width=True)

    c1, c2 = st.columns(2)
    with c1:
        st.subheader("🚀 Atak Yapanlar (Artış)")
        gainers = df[df['score_diff'] > 1.0].sort_values(by='score_diff', ascending=False).head(10)
        st.dataframe(gainers[cols].rename(columns=dict(zip(cols, names))), use_container_width=True)
    
    with c2:
        st.subheader("⚠️ Çıkış Radarı (Düşüş)")
        losers = df[df['score_diff'] < -1.0].sort_values(by='score_diff', ascending=True).head(10)
        st.dataframe(losers[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Fark'], cmap='Reds_r'), use_container_width=True)
else:
    st.info("Veri bekleniyor...")
