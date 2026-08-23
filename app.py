import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Institutional Terminal", layout="wide")
st.title("🛡️ US Kurumsal Akış & Opsiyon Radarı")

if os.path.exists("sonuclar.csv"):
    try:
        df = pd.read_csv("sonuclar.csv")
        
        # SÜTUN KONTROLÜ: Yeni derivatif sütunlarını denetle
        required_cols = ['ticker', 'quant_score', 'score_diff', 'pct_oi_mom', 'pct_skew', 'squeeze_skor']
        for col in required_cols:
            if col not in df.columns:
                df[col] = 0.0

        st.subheader("🏆 Opsiyon ve Squeeze Onaylı Liderler")
        mapping = {
            'ticker': 'Hisse', 'quant_score': 'Skor', 'score_diff': 'Fark',
            'pct_oi_mom': 'Opsiyon OI %', 'pct_skew': 'Skew %', 'squeeze_skor': 'Squeeze'
        }
        
        disp_df = df[required_cols].rename(columns=mapping)
        st.dataframe(
            disp_df.style.background_gradient(subset=['Skor'], cmap='YlGn'),
            use_container_width=True
        )
        st.info("💡 Sütunlar 0 görünüyorsa, yeni sürümün ilk taramasının bitmesini bekleyin.")

    except Exception as e:
        st.error(f"Veri işleme hatası: {e}")
else:
    st.info("Veri bekleniyor...")
