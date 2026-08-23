import streamlit as st
import pandas as pd
import numpy as np
import os

st.set_page_config(page_title="US Quant Terminal Pro", layout="wide")

st.title("🇺🇸 US Quant Radar: Squeeze & Momentum")
st.caption("S&P500 & Nasdaq-100: RVOL, Short Squeeze, Insider ve Opsiyon Analizi")

# --- VERI YUKLEME VE HATA KORUMASI ---
if os.path.exists("sonuclar.csv"):
    try:
        df = pd.read_csv("sonuclar.csv")
        
        if df.empty:
            st.warning("⚠️ Tarama dosyası şu an boş. Lütfen GitHub Actions'ın bitmesini bekleyin.")
            st.stop()

        # KRITIK: Eksik sütun kontrolü (Hata almamak için)
        # Eğer yeni güncellemeyle gelen sütunlar henüz CSV'de yoksa onları 0 olarak yarat
        check_cols = {
            'ticker': 'N/A', 'quant_score': 0.0, 'score_diff': 0.0, 
            'squeeze_skor': 0.0, 'pct_pc_rank': 0.0, 'rvol_ratio': 1.0, 
            'change_%': 0.0, 'insider_bonus': 0.0
        }
        
        for col, default_val in check_cols.items():
            if col not in df.columns:
                df[col] = default_val

        # Sayıları Yuvarla
        num_cols = ['quant_score', 'score_diff', 'pct_pc_rank', 'squeeze_skor', 'rvol_ratio', 'change_%']
        for col in num_cols:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).round(2)

        # --- 1. SIDEBAR: HİSSE TAKİP ---
        st.sidebar.header("🔍 US Hisse Takip")
        search_ticker = st.sidebar.text_input("Hisse Kodu (Örn: TSLA):").upper()
        
        if search_ticker:
            h_data = df[df['ticker'] == search_ticker]
            if not h_data.empty:
                score = h_data['quant_score'].iloc[0]
                diff = h_data['score_diff'].iloc[0]
                status = "🚀 GÜÇLÜ" if score > 70 else ("⚠️ ZAYIF" if score < 45 else "NÖTR")
                st.sidebar.metric(f"{search_ticker} Skoru", score, f"{diff:+.2f}")
                st.sidebar.write(f"**Durum:** {status}")
            else:
                st.sidebar.warning("Hisse bulunamadı.")

        # --- 2. ANA TABLOLAR ---
        cols = ['ticker', 'quant_score', 'score_diff', 'pct_pc_rank', 'squeeze_skor', 'rvol_ratio', 'change_%', 'insider_bonus']
        mapping = {
            'ticker': 'Hisse', 'quant_score': 'Skor', 'score_diff': 'Fark', 
            'pct_pc_rank': 'Opsiyon %', 'squeeze_skor': 'Squeeze %', 
            'rvol_ratio': 'RVOL', 'change_%': 'Fiyat %', 'insider_bonus': 'Insider'
        }

        st.subheader("🏆 US Quant Liderleri (Top 20)")
        top_df = df.sort_values(by='quant_score', ascending=False).head(20)[cols].rename(columns=mapping)
        st.dataframe(top_df.style.background_gradient(subset=['Skor'], cmap='RdYlGn'), use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🔥 Atak Yapanlar")
            gainers = df[df['score_diff'] > 0.5].sort_values(by='score_diff', ascending=False).head(10)[cols].rename(columns=mapping)
            st.dataframe(gainers, use_container_width=True)

        with col2:
            st.subheader("🛑 Çıkış Radarı")
            losers = df[df['score_diff'] < -0.5].sort_values(by='score_diff', ascending=True).head(10)[cols].rename(columns=mapping)
            st.dataframe(losers.style.background_gradient(subset=['Fark'], cmap='Reds_r'), use_container_width=True)

    except Exception as e:
        st.error(f"Sistem Hatası: {e}")
        st.info("İpucu: Sütun hatası alıyorsanız lütfen GitHub Actions üzerinden taramayı manuel başlatın.")
else:
    st.info("Veri bekleniyor... GitHub Actions çalışınca burada görünecek.")
