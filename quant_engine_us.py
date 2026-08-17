import numpy as np
import pandas as pd
import yfinance as yf

GECMIS_DOSYA = "gecmis_veri.csv"

def gunluk_veri_cek(tickers):
    # Toplu veri cekimi
    data = yf.download(tickers, period="2d", interval="1d", progress=False)['Close']
    df_bugun = []
    for t in tickers:
        try:
            if t in data.columns and len(data[t].dropna()) >= 2:
                bugun = data[t].iloc[-1]
                dun = data[t].iloc[-2]
                degisim = (bugun / dun - 1) * 100
                # Hacim icin ayri cekim (yfinance kısıtı)
                vol = yf.Ticker(t).fast_info['last_volume']
                df_bugun.append({"ticker": t, "close": bugun, "volume": vol, "change_%": degisim})
        except: continue
    return pd.DataFrame(df_bugun)

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map):
    if df.empty: return df

    # 1. RVOL
    rvol_list = []
    for _, row in df.iterrows():
        gecmis = df_gecmis[df_gecmis['ticker'] == row['ticker']]['volume'].tail(20)
        rvol = row['volume'] / gecmis.mean() if len(gecmis) >= 5 else 1.0
        rvol_list.append(rvol)
    df['rvol_ratio'] = rvol_list
    
    # 2. Yuzdelik Dilimler
    df['pct_rvol'] = df['rvol_ratio'].rank(pct=True) * 100
    df['pct_change'] = df['change_%'].rank(pct=True) * 100
    
    # 3. Yapisal Kapi Entegrasyonu
    df = df.merge(df_yapisal[['ticker', 'yapisal_skor']], on='ticker', how='left')
    df['yapisal_skor'] = df['yapisal_skor'].fillna(50.0)
    
    # 4. Insider Bonus
    df['insider_bonus'] = df['ticker'].map(insider_bonus_map).fillna(0)
    
    # 5. FINAL FORMUL (Plandaki agirliklar)
    df['quant_score'] = (
        (df['pct_rvol'] * 0.40) + 
        (df['pct_change'] * 0.25) + 
        (df['yapisal_skor'] * 0.25) + 
        df['insider_bonus']
    )
    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
