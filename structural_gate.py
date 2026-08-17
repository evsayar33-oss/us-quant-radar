import os
import requests
import pandas as pd
import yfinance as yf
import numpy as np

YAPISAL_DOSYA = "yapisal_gate.csv"

def get_float_and_short_fallback(ticker):
    """yfinance uzerinden Short ve Float verisi ceker (Yedek Hat)."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        short_ratio = info.get("shortPercentOfFloat", np.nan)
        dtc = info.get("shortRatio", np.nan) # Days to cover
        fs = info.get("floatShares", np.nan)
        return short_ratio * 100 if short_ratio else np.nan, dtc, fs
    except:
        return np.nan, np.nan, np.nan

def yapisal_gate_hesapla(tickers, df_gecmis):
    results = []
    print(f"{len(tickers)} hisse icin yapisal kapi hesaplaniyor...")
    
    for ticker in tickers:
        # Plandaki short_pct_float ve days_to_cover verilerini cek
        short_pct, dtc, fs = get_float_and_short_fallback(ticker)
        
        results.append({
            "ticker": ticker,
            "short_pct_float": short_pct,
            "days_to_cover": dtc,
            "float_shares": fs
        })
    
    df = pd.DataFrame(results)
    # Yuzdelik dilimleme
    df['pct_short_float'] = df['short_pct_float'].rank(pct=True) * 100
    df['pct_dtc'] = df['days_to_cover'].rank(pct=True) * 100
    df['yapisal_skor'] = (df['pct_short_float'] * 0.5) + (df['pct_dtc'] * 0.5)
    
    # Eksikleri medyanla doldur
    df['yapisal_skor'] = df['yapisal_skor'].fillna(df['yapisal_skor'].median()).fillna(50.0)
    df.to_csv(YAPISAL_DOSYA, index=False)
    return df

def yapisal_gate_yukle():
    if os.path.exists(YAPISAL_DOSYA):
        return pd.read_csv(YAPISAL_DOSYA)
    return pd.DataFrame(columns=["ticker", "yapisal_skor"])
