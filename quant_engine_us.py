import numpy as np
import pandas as pd
import yfinance as yf

GECMIS_DOSYA = "gecmis_veri.csv"

def get_option_sentiment(ticker):
    """Hisse bazli Put/Call rasyosunu ceker."""
    try:
        t = yf.Ticker(ticker)
        options = t.options
        if not options: return 0.7 
        opt_chain = t.option_chain(options[0])
        puts_vol = opt_chain.puts['volume'].sum()
        calls_vol = opt_chain.calls['volume'].sum()
        if calls_vol == 0: return 1.5
        return float(puts_vol / calls_vol)
    except:
        return 0.7

def gunluk_veri_cek(tickers):
    """Toplu fiyat ve hacim verisi cekimi."""
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
                        "close": float(p_series.iloc[-1]),
                        "volume": float(v_series.iloc[-1]),
                        "change_%": float((p_series.iloc[-1]/p_series.iloc[-2]-1)*100)
                    })
        except: continue
    return pd.DataFrame(df_bugun)

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map, option_data_map):
    if df.empty: return df

    # 1. RVOL (Hacim Z-Skoru)
    z_vol_list = []
    for _, row in df.iterrows():
        if not df_gecmis.empty:
            hist_v = df_gecmis[df_gecmis['ticker'] == row['ticker']]['volume'].tail(20)
            z = (row['volume'] - hist_v.mean()) / (hist_v.std() + 1e-9) if len(hist_v) >= 5 else 0
            z_vol_list.append(np.clip(z, -3, 3))
        else:
            z_vol_list.append(0)
    df['vol_z'] = z_vol_list
    df['rvol_ratio'] = df['vol_z'] # Dashboard uyumu icin
    
    # 2. Opsiyon Rank (Adaptif)
    df['pc_ratio'] = df['ticker'].map(option_data_map).fillna(0.7)
    df['pct_pc_rank'] = (1 - df['pc_ratio'].rank(pct=True)) * 100
    
    # 3. Yapisal ve Insider Birlestirme
    df = df.merge(df_yapisal[['ticker', 'squeeze_skor']], on='ticker', how='left')
    df['squeeze_skor'] = df['squeeze_skor'].fillna(50.0)
    df['insider_bonus'] = df['ticker'].map(insider_bonus_map).fillna(0)
    
    # 4. Final Skor
    df['quant_score'] = (
        ((df['vol_z'] * 10 + 50) * 0.30) +
        (df['change_%'].rank(pct=True) * 20) +
        (df['squeeze_skor'] * 0.30) +
        (df['pct_pc_rank'] * 0.20) +
        df['insider_bonus']
    )

    # 5. Skor Farki
    df['score_diff'] = 0.0
    if not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        son_tarih = df_gecmis['tarih'].max()
        df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
        eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        df['score_diff'] = df['quant_score'] - df['ticker'].map(eski_map).fillna(df['quant_score'])

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
