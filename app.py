import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Quant Radar", layout="wide")

st.title("🇺🇸 US Quant Radar (S&P500 & Nasdaq-100)")
st.caption("RVOL, Fiyat İvmesi, Short Squeeze ve Insider Alım Analizi")

# 1. Ana Sonuclar Tablosu
if os.path.exists("sonuclar.csv"):
    df = pd.read_csv("sonuclar.csv")
    
    st.metric("Taranan Toplam Hisse", len(df))
    
    st.subheader("🚀 En Yüksek Quant Skorlu Hisseler")
    
    # Sütunları düzenle
    cols = ['ticker', 'quant_score', 'rvol_ratio', 'change_%', 'yapisal_skor', 'insider_bonus']
    disp_df = df[cols].copy()
    disp_df.columns = ['Hisse', 'Quant Skor', 'RVOL', 'Günlük %', 'Yapısal Skor', 'Insider']
    
    # Skor bazlı renklendirme
    st.dataframe(
        disp_df.style.format(precision=2).background_gradient(subset=['Quant Skor'], cmap='RdYlGn'),
        use_container_width=True
    )
    
    st.info("💡 RVOL > 1.5 ve Yapısal Skor > 70 olan hisseler squeeze (sıkıştırma) potansiyeli taşır.")
else:
    st.warning("Henüz tarama verisi oluşmadı. GitHub Actions ilk çalışmayı bitirdiğinde burada görünecek.")

# 2. Yapısal Kapi Detayları (Ayrı bir sekme veya expander)
if os.path.exists("yapisal_gate.csv"):
    with st.expander("🔍 Yapısal Kapı Detayları (Short Interest & Days-to-Cover)"):
        df_y = pd.read_csv("yapisal_gate.csv")
        st.write("Bu tablo 2 haftada bir güncellenen FINRA verilerini içerir.")
        st.dataframe(df_y, use_container_width=True)

st.sidebar.markdown("### Sistem Notları")
st.sidebar.write("- Veriler ABD kapanışından sonra (TSİ 23:30) güncellenir.")
st.sidebar.write("- Insider verisi SEC EDGAR üzerinden çekilir.")
