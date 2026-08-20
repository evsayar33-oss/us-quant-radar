import numpy as np
import pandas as pd
import yfinance as yf

GECMIS_DOSYA = "gecmis_veri.csv"

def gunluk_veri_cek(tickers):
    # Toplu veri cekimi
    data = yf.download(tickers, period="5d", interval="1d", progress=False)
    closes = data['Close'].ffill()
    volumes = data['Volume'].ffill()
    
    df_bugun = []
    for t in tickers:
        try:
            if t in closes.columns:
                p_series = closes[t].dropna()
                v_series = volumes[t].dropna()
                if len(p_series) >= 2:
                    df_bugun.append({
                        "ticker": t,
                        "close": p_series.iloc[-1],
                        "volume": v_series.iloc[-1],
                        "change_%": (p_series.iloc[-1]/p_series.iloc[-2]-1)*100
                    })
        except: continue
    return pd.DataFrame(df_bugun)

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map, option_data_map):
    if df.empty: return df

    # 1. HACIM Z-SCORE (RVOL)
    z_vol_list = []
    for _, row in df.iterrows():
        hist_v = df_gecmis[df_gecmis['ticker'] == row['ticker']]['volume'].tail(20)
        if len(hist_v) >= 5:
            # Z-Score: (Bugun - Ortalama) / StdDev
            z = (row['volume'] - hist_v.mean()) / (hist_v.std() + 1e-9)
            z_vol_list.append(np.clip(z, -3, 3)) # Sinyali 3 sigma ile sınırla
        else:
            z_vol_list.append(0)
    df['vol_z'] = z_vol_list
    
    # 2. FIYAT DEGISIM Z-SCORE
    df['pct_change_rank'] = df['change_%'].rank(pct=True) * 100
    
    # 3. Yapisal Verileri Birlestir
    df = df.merge(df_yapisal[['ticker', 'squeeze_skor', 'is_micro']], on='ticker', how='left')
    df['squeeze_skor'] = df['squeeze_skor'].fillna(50.0)
    
    # 4. Opsiyon ve Insider Bonus
    df['option_rank'] = df['ticker'].map(option_data_map).fillna(50.0)
    df['insider_bonus'] = df['ticker'].map(insider_bonus_map).fillna(0)
    
    # --- FINAL QUANT SCORE (Z-SCORE TABANLI) ---
    # Agirliklar: %30 Hacim Z + %20 Fiyat Rank + %30 Squeeze Skoru + %20 Opsiyon
    df['quant_score'] = (
        (df['vol_z'] * 10 + 50) * 0.30 + # Z-Skoru 0-100 arasina cekiyoruz
        (df['pct_change_rank'] * 0.20) +
        (df['squeeze_skor'] * 0.30) +
        (df['option_rank'] * 0.20) +
        df['insider_bonus']
    )
    
    # 5. Skor Değişimi (Çıkış Sinyali için)
    df['score_diff'] = 0.0
    if not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        df_son = df_gecmis[df_gecmis['tarih'] == df_gecmis['tarih'].max()]
        eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        df['score_diff'] = df['quant_score'] - df['ticker'].map(eski_map).fillna(df['quant_score'])

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
