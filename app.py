import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="US Quant Terminal Pro", layout="wide")

st.title("🇺🇸 US Quant Radar: Squeeze & Momentum")
st.caption("S&P500 & Nasdaq-100: RVOL, Short Squeeze, Insider ve Opsiyon Analizi")

# Dosya Yükleme
if os.path.exists("sonuclar.csv") and os.path.exists("gecmis_veri.csv"):
    df = pd.read_csv("sonuclar.csv")
    df_gecmis = pd.read_csv("gecmis_veri.csv")
    
    # Sayıları Yuvarla
    for col in ['quant_score', 'score_diff', 'pct_pc_rank', 'squeeze_skor']:
        if col in df.columns: df[col] = df[col].round(2)

    # --- 1. SIDEBAR: HİSSE TAKİP ---
    st.sidebar.header("🔍 US Hisse Takip")
    search_ticker = st.sidebar.text_input("Hisse Kodu (Örn: TSLA):").upper()
    
    if search_ticker:
        h_data = df[df['ticker'] == search_ticker]
        if not h_data.empty:
            score = h_data['quant_score'].iloc[0]
            diff = h_data['score_diff'].iloc[0]
            sqz = h_data['squeeze_skor'].iloc[0]
            
            status = "🚀 GÜÇLÜ BOĞA" if score > 70 else ("⚠️ ZAYIFLAMA" if score < 45 else "NÖTR / İZLE")
            st.sidebar.metric(f"{search_ticker} Skoru", score, f"{diff:+.2f}")
            st.sidebar.markdown(f"**Durum:** {status}")
            st.sidebar.write(f"**Squeeze Potansiyeli:** %{sqz}")
            
            st.sidebar.write("Son 5 Günlük Skor Trendi:")
            trend = df_gecmis[df_gecmis['ticker'] == search_ticker].tail(5)[['tarih', 'quant_score']]
            st.sidebar.table(trend)
        else:
            st.sidebar.warning("Hisse bulunamadı.")

    # --- 2. ANA TABLOLAR ---
    cols = ['ticker', 'quant_score', 'score_diff', 'squeeze_skor', 'pct_pc_rank', 'rvol_ratio', 'change_%', 'insider_bonus']
    mapping = {
        'ticker': 'Hisse', 'quant_score': 'Skor', 'score_diff': 'Fark', 
        'squeeze_skor': 'Squeeze %', 'pct_pc_rank': 'Opsiyon Gücü', 
        'rvol_ratio': 'RVOL', 'change_%': 'Günlük %', 'insider_bonus': 'Insider'
    }

    # TABLO 1: LİDERLER
    st.subheader("🏆 US Quant Liderleri (Top 20)")
    top_df = df.head(20)[cols].rename(columns=mapping)
    st.dataframe(top_df.style.format(precision=2).background_gradient(subset=['Skor'], cmap='RdYlGn'), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔥 Atak Yapanlar (İvme)")
        gainers = df[df['score_diff'] > 1.0].sort_values(by='score_diff', ascending=False).head(10)
        st.dataframe(gainers[cols].rename(columns=mapping).style.format(precision=2).background_gradient(subset=['Fark'], cmap='Greens'), use_container_width=True)

    with col2:
        st.subheader("🛑 Çıkış Radarı (Güç Kaybı)")
        losers = df[df['score_diff'] < -1.0].sort_values(by='score_diff', ascending=True).head(10)
        st.dataframe(losers[cols].rename(columns=mapping).style.format(precision=2).background_gradient(subset=['Fark'], cmap='Reds_r'), use_container_width=True)

    st.caption("💡 Not: Squeeze % ne kadar yüksekse, açığa satış yapanların panik alımı yapma ihtimali o kadar artar.")
else:
    st.info("Veri bekleniyor... Lütfen GitHub Actions sekmesinden 'Daily Trigger'ı çalıştırın.")
