import numpy as np
import pandas as pd
import yfinance as yf

GECMIS_DOSYA = "gecmis_veri.csv"

def gunluk_veri_cek(tickers):
    """yfinance üzerinden toplu veri çekimi ve temizliği."""
    # Toplu veri çekimi
    data = yf.download(tickers, period="2d", interval="1d", progress=False)['Close']
    df_bugun = []
    
    for t in tickers:
        try:
            if t in data.columns:
                ticker_data = data[t].dropna()
                if len(ticker_data) >= 2:
                    bugun = ticker_data.iloc[-1]
                    dun = ticker_data.iloc[-2]
                    degisim = (bugun / dun - 1) * 100
                    
                    # Hacim verisini yf.Ticker üzerinden hızlıca alalım
                    # (Toplu çekimde hacim bazen sorun çıkarabiliyor)
                    vol = yf.Ticker(t).fast_info.get('last_volume', 0)
                    
                    df_bugun.append({
                        "ticker": t, 
                        "close": float(bugun), 
                        "volume": float(vol), 
                        "change_%": float(degisim)
                    })
        except:
            continue
    return pd.DataFrame(df_bugun)

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map):
    if df.empty: return df

    # 1. RVOL (Göreceli Hacim)
    rvol_list = []
    for _, row in df.iterrows():
        if not df_gecmis.empty:
            gecmis = df_gecmis[df_gecmis['ticker'] == row['ticker']]['volume'].tail(20)
            rvol = row['volume'] / gecmis.mean() if len(gecmis) >= 5 else 1.0
        else:
            rvol = 1.0
        rvol_list.append(rvol)
    df['rvol_ratio'] = rvol_list
    
    # 2. Yüzdelik Dilimler
    df['pct_rvol'] = df['rvol_ratio'].rank(pct=True) * 100
    df['pct_change'] = df['change_%'].rank(pct=True) * 100
    
    # 3. Yapısal Kapı Entegrasyonu
    if not df_yapisal.empty:
        df = df.merge(df_yapisal[['ticker', 'yapisal_skor']], on='ticker', how='left')
    else:
        df['yapisal_skor'] = 50.0
    df['yapisal_skor'] = df['yapisal_skor'].fillna(50.0)
    
    # 4. Insider Bonus
    df['insider_bonus'] = df['ticker'].map(insider_bonus_map).fillna(0)
    
    # 5. Ana Skor
    df['quant_score'] = (df['pct_rvol'] * 0.40) + (df['pct_change'] * 0.25) + (df['yapisal_skor'] * 0.25) + df['insider_bonus']

    # 6. Skor Farkı (Çıkış Sinyali İçin)
    df['score_diff'] = 0.0
    if not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        son_tarih = df_gecmis['tarih'].max()
        df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
        eski_skor_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        df['score_diff'] = df['quant_score'] - df['ticker'].map(eski_skor_map).fillna(df['quant_score'])

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
