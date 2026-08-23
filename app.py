import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Institutional Terminal", layout="wide")
st.title("🛡️ US Kurumsal Akış & Opsiyon Radarı")

if os.path.exists("sonuclar.csv") and os.path.exists("gecmis_veri.csv"):
    try:
        df = pd.read_csv("sonuclar.csv")
        df_gecmis = pd.read_csv("gecmis_veri.csv")
        
        # Sayıları yuvarla
        for col in ['quant_score', 'score_diff', 'pct_pc_rank', 'squeeze_skor', 'vol_z']:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round(2)

        # --- 1. SIDEBAR: HİSSE SORGULAMA ---
        st.sidebar.header("🔍 US Hisse Takip")
        search_ticker = st.sidebar.text_input("Hisse Kodu (Örn: TSLA):").upper()
        
        if search_ticker:
            h_data = df[df['ticker'] == search_ticker]
            if not h_data.empty:
                score = h_data['quant_score'].iloc[0]
                diff = h_data['score_diff'].iloc[0]
                st.sidebar.metric(f"{search_ticker} Skoru", score, f"{diff:+.2f}")
                
                st.sidebar.write("Son 5 Günlük Trend:")
                trend = df_gecmis[df_gecmis['ticker'] == search_ticker].tail(5)[['tarih', 'quant_score']]
                st.sidebar.table(trend)
            else:
                st.sidebar.warning("Hisse bulunamadı.")

        # --- 2. ANA TABLOLAR ---
        cols = ['ticker', 'quant_score', 'score_diff', 'pct_pc_rank', 'squeeze_skor', 'vol_z', 'change_%']
        names = ['Hisse', 'Skor', 'Fark', 'Opsiyon %', 'Squeeze', 'Hacim Z', 'Fiyat %']

        st.subheader("🏆 Opsiyon ve Squeeze Onaylı Liderler")
        st.dataframe(df.head(20)[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Skor'], cmap='YlGn'), use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            st.subheader("🚀 Atak Yapanlar")
            gainers = df[df['score_diff'] > 1.0].sort_values(by='score_diff', ascending=False).head(10)
            st.dataframe(gainers[cols].rename(columns=dict(zip(cols, names))), use_container_width=True)
        with c2:
            st.subheader("⚠️ Çıkış Radarı")
            losers = df[df['score_diff'] < -1.0].sort_values(by='score_diff', ascending=True).head(10)
            st.dataframe(losers[cols].rename(columns=dict(zip(cols, names))).style.background_gradient(subset=['Fark'], cmap='Reds_r'), use_container_width=True)

    except Exception as e:
        st.error(f"Hata: {e}")
else:
    st.info("Veri bekleniyor...")
