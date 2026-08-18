import numpy as np
import pandas as pd
import yfinance as yf

GECMIS_DOSYA = "gecmis_veri.csv"

def get_option_sentiment(ticker):
    """Hisse bazlı Put/Call hacim verisini çeker."""
    try:
        t = yf.Ticker(ticker)
        options = t.options
        if not options: return 0.7 
        opt_chain = t.option_chain(options[0])
        puts_vol = opt_chain.puts['volume'].sum()
        calls_vol = opt_chain.calls['volume'].sum()
        if calls_vol == 0: return 1.5
        return puts_vol / calls_vol
    except:
        return 0.7

def gunluk_veri_cek(tickers):
    data = yf.download(tickers, period="2d", interval="1d", progress=False)['Close']
    df_bugun = []
    for t in tickers:
        try:
            if t in data.columns:
                ticker_data = data[t].dropna()
                if len(ticker_data) >= 2:
                    bugun, dun = ticker_data.iloc[-1], ticker_data.iloc[-2]
                    vol = yf.Ticker(t).fast_info.get('last_volume', 0)
                    df_bugun.append({"ticker": t, "close": float(bugun), "volume": float(vol), "change_%": (bugun/dun-1)*100})
        except: continue
    return pd.DataFrame(df_bugun)

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map, option_data_map):
    if df.empty: return df

    # 1. RVOL & Fiyat Dilimleri
    rvol_list = []
    for _, row in df.iterrows():
        gecmis = df_gecmis[df_gecmis['ticker'] == row['ticker']]['volume'].tail(20) if not df_gecmis.empty else []
        rvol_list.append(row['volume'] / gecmis.mean() if len(gecmis) >= 5 else 1.0)
    df['rvol_ratio'] = rvol_list
    
    df['pct_rvol'] = df['rvol_ratio'].rank(pct=True) * 100
    df['pct_change'] = df['change_%'].rank(pct=True) * 100
    
    # 2. Yapısal & Insider
    df = df.merge(df_yapisal[['ticker', 'yapisal_skor']], on='ticker', how='left')
    df['yapisal_skor'] = df['yapisal_skor'].fillna(50.0)
    df['insider_bonus'] = df['ticker'].map(insider_bonus_map).fillna(0)
    
    # 3. DİNAMİK OPSİYON ANALİZİ (ADAPTİF EŞİK)
    df['pc_ratio'] = df['ticker'].map(option_data_map).fillna(0.7)
    # Put/Call rasyosu ne kadar düşükse, puan o kadar yüksek olmalı (Ters rank)
    df['pct_pc_rank'] = (1 - df['pc_ratio'].rank(pct=True)) * 100
    
    # 4. FINAL FORMÜL (Tümü adaptif yüzdelik dilimlerden oluşur)
    # Artık 0.5/0.7 gibi rakamlar yok, sadece "piyasadaki diğerlerine göre durumu" var.
    df['quant_score'] = (
        (df['pct_rvol'] * 0.30) + 
        (df['pct_change'] * 0.20) + 
        (df['yapisal_skor'] * 0.25) + 
        (df['pct_pc_rank'] * 0.15) + 
        df['insider_bonus']
    )

    # 5. Fark Hesabı
    df['score_diff'] = 0.0
    if not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        df_son = df_gecmis[df_gecmis['tarih'] == df_gecmis['tarih'].max()]
        eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        df['score_diff'] = df['quant_score'] - df['ticker'].map(eski_map).fillna(df['quant_score'])

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
