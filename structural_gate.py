import yfinance as yf
import pandas as pd
import numpy as np
import os

YAPISAL_DOSYA = "yapisal_gate.csv"

def hesapla_squeeze_skoru(ticker):
    """Hisse bazli squeeze potansiyelini 0-100 arasi puanlar."""
    try:
        t = yf.Ticker(ticker)
        info = t.info
        
        short_pct = info.get("shortPercentOfFloat", 0) # Aciga satis orani
        dtc = info.get("shortRatio", 0)               # Days to cover
        mcap = info.get("marketCap", 1e10)            # Piyasa degeri
        
        if not short_pct: short_pct = 0
        
        # SQUEEZE FORMULU: (Short % * 5) + (DTC * 10) - (Log10(MCAP))
        # Kucuk piyasa degeri ve yuksek short orani puani yukseltir.
        raw_score = (short_pct * 100 * 3) + (dtc * 5)
        
        # Puanı 0-100 arasina normalize et (Max %30 short interest ve 10 DTC uzeri 100 puan)
        final_score = np.clip(raw_score, 0, 100)
        
        # Mikro-Cap Kontrolü (< 300M$)
        is_micro = 1 if mcap < 300000000 else 0
        
        return {
            "ticker": ticker,
            "short_interest_%": round(short_pct * 100, 2),
            "days_to_cover": round(dtc, 2),
            "squeeze_skor": round(final_score, 2),
            "is_micro": is_micro
        }
    except:
        return {"ticker": ticker, "short_interest_%": 0, "days_to_cover": 0, "squeeze_skor": 50, "is_micro": 0}

def yapisal_gate_hesapla(tickers, df_gecmis):
    results = []
    print(f"Squeeze analizi basladi...")
    for ticker in tickers:
        data = hesapla_squeeze_skoru(ticker)
        results.append(data)
    
    df = pd.DataFrame(results)
    df.to_csv(YAPISAL_DOSYA, index=False)
    return df

def yapisal_gate_yukle():
    if os.path.exists(YAPISAL_DOSYA):
        return pd.read_csv(YAPISAL_DOSYA)
    return pd.DataFrame(columns=["ticker", "squeeze_skor", "is_micro"])
