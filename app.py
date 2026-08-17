import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Quant Terminal", layout="wide")

st.title("🇺🇸 US Quant Nicel Radar & Çıkış Sistemi")
st.caption("S&P500 & Nasdaq-100: RVOL, Squeeze ve Insider Analizi")

# Dosya Kontrolleri
if os.path.exists("sonuclar.csv") and os.path.exists("gecmis_veri.csv"):
    df = pd.read_csv("sonuclar.csv")
    df_gecmis = pd.read_csv("gecmis_veri.csv")
    
    # 1. SIDEBAR: HİSSE SORGULAMA (SATAYIM MI?)
    st.sidebar.header("🔍 US Hisse Takip")
    search_ticker = st.sidebar.text_input("Hisse Kodu (Örn: NVDA):").upper()
    
    if search_ticker:
        hisse_data = df[df['ticker'] == search_ticker]
        if not hisse_data.empty:
            score = hisse_data['quant_score'].iloc[0]
            diff = hisse_data['score_diff'].iloc[0] if 'score_diff' in hisse_data.columns else 0
            
            if score >= 75: status, s_col = "GÜÇLÜ TUT (BOĞA)", "green"
            elif score >= 55: status, s_col = "İZLE / KARARSIZ", "orange"
            else: status, s_col = "TEHLİKE / ÇIK (AYI)", "red"

            st.sidebar.subheader(f"Analiz: {search_ticker}")
            st.sidebar.metric("Güncel Skor", f"{score:.2f}", f"{diff:+.2f}")
            st.sidebar.markdown(f"**Durum:** :{s_col}[{status}]")
            
            st.sidebar.write("Son 5 Günlük Skor Trendi:")
            trend = df_gecmis[df_gecmis['ticker'] == search_ticker].tail(5)[['tarih', 'quant_score']]
            st.sidebar.table(trend)
        else:
            st.sidebar.warning("Hisse bulunamadı veya henüz taranmadı.")

    # 2. ANA TABLOLAR
    cols = ['ticker', 'quant_score', 'score_diff', 'rvol_ratio', 'change_%', 'yapisal_skor', 'insider_bonus']
    mapping = {'ticker': 'Hisse', 'quant_score': 'Skor', 'score_diff': 'Fark', 'rvol_ratio': 'RVOL', 'change_%': 'Günlük %', 'yapisal_skor': 'Yapısal', 'insider_bonus': 'Insider'}

    st.subheader("🏆 Liderler (Top 20)")
    top_df = df.head(20)[cols].rename(columns=mapping)
    st.dataframe(top_df.style.format(precision=2).background_gradient(subset=['Skor'], cmap='RdYlGn'), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🚀 Atak Yapanlar")
        gainers = df.sort_values(by='score_diff', ascending=False).head(10)[cols].rename(columns=mapping)
        st.dataframe(gainers.style.format(precision=2).background_gradient(subset=['Fark'], cmap='Greens'), use_container_width=True)

    with col2:
        st.subheader("⚠️ Çıkış Radarı (Güç Kaybedenler)")
        losers = df.sort_values(by='score_diff', ascending=True).head(10)[cols].rename(columns=mapping)
        st.dataframe(losers.style.format(precision=2).background_gradient(subset=['Fark'], cmap='Reds_r'), use_container_width=True)

else:
    st.info("Veri bekleniyor... GitHub Actions çalışınca burada görünecek.")
