import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Quant Radar", layout="wide")

st.title("🇺🇸 US Quant Radar (S&P500 & Nasdaq-100)")
st.caption("RVOL, Fiyat İvmesi, Short Squeeze ve Insider Alım Analizi")

if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
    st.metric("Taranan Toplam Hisse", len(df))
    st.subheader("🚀 En Yüksek Quant Skorlu Hisseler")
    
    kolonlar = ['ticker', 'quant_score', 'rvol_ratio', 'change_%', 'yapisal_skor', 'insider_bonus']
    # Sadece mevcut olan kolonları seç (Hata almamak için)
    mevcut_kolonlar = [k for k in kolonlar if k in df.columns]
    disp_df = df[mevcut_kolonlar].copy()
    
    # Başlıkları Türkçeleştir
    mapping = {
        'ticker': 'Hisse', 'quant_score': 'Quant Skor', 'rvol_ratio': 'RVOL',
        'change_%': 'Günlük %', 'yapisal_skor': 'Yapısal Skor', 'insider_bonus': 'Insider'
    }
    disp_df = disp_df.rename(columns=mapping)

    # Tabloyu renklendir (Matplotlib hatasını bu blok çözer)
    st.dataframe(
        disp_df.style.format(precision=2).background_gradient(subset=['Quant Skor'], cmap='RdYlGn'),
        use_container_width=True
    )
    
    st.info("💡 RVOL > 1.5 ve Yapısal Skor > 70 olan hisseler squeeze potansiyeli taşır.")
else:
    st.warning("Veri bulunamadı. GitHub Actions işleminin bitmesini bekleyin.")
