import numpy as np
import pandas as pd
import yfinance as yf
import os

GECMIS_DOSYA = "gecmis_veri.csv"
MOM_PENCERE = 5 

def gunluk_veri_cek(tickers):
    """yfinance üzerinden toplu fiyat ve hacim verisi çeker."""
    try:
        data = yf.download(tickers, period="5d", interval="1d", progress=False)
        closes = data['Close'].ffill()
        volumes = data['Volume'].ffill()
        
        df_bugun = []
        for t in tickers:
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
        return pd.DataFrame(df_bugun)
    except Exception as e:
        print(f"Veri cekme hatasi: {e}")
        return pd.DataFrame()

def get_advanced_option_metrics(ticker):
    """Opsiyon OI Momentumu ve Skew verilerini hesaplar."""
    try:
        t = yf.Ticker(ticker)
        options = t.options
        if not options: return 0.0, 0.7
        
        total_puts_oi = 0
        total_calls_oi = 0
        for date in options[:2]: # İlk iki vade yeterli
            opt_chain = t.option_chain(date)
            total_puts_oi += opt_chain.puts['openInterest'].sum()
            total_calls_oi += opt_chain.calls['openInterest'].sum()
            
        current_total_oi = total_puts_oi + total_calls_oi
        skew_proxy = total_puts_oi / (total_calls_oi + 1e-9)
        return float(current_total_oi), round(float(skew_proxy), 4)
    except:
        return 0.0, 0.7

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map, opt_metrics_map):
    if df.empty: return df

    # 1. RVOL (Z-Score)
    z_vol_list = []
    for _, row in df.iterrows():
        if not df_gecmis.empty and row['ticker'] in df_gecmis['ticker'].values:
            hist_v = df_gecmis[df_gecmis['ticker'] == row['ticker']]['volume'].tail(20)
            z = (row['volume'] - hist_v.mean()) / (hist_v.std() + 1e-9) if len(hist_v) >= 5 else 0
            z_vol_list.append(np.clip(z, -3, 3))
        else:
            z_vol_list.append(0)
    df['vol_z'] = z_vol_list
    df['rvol_ratio'] = df['vol_z']

    # 2. Opsiyon OI Momentum ve Skew
    oi_mom_list, skew_list = [], []
    for _, row in df.iterrows():
        t = row['ticker']
        curr_oi, curr_skew = opt_metrics_map.get(t, (0.0, 0.7))
        
        if not df_gecmis.empty and 'option_oi' in df_gecmis.columns:
            hist_oi = df_gecmis[df_gecmis['ticker'] == t]['option_oi'].tail(MOM_PENCERE)
            oi_mom = curr_oi / hist_oi.mean() if len(hist_oi) >= 2 and hist_oi.mean() > 0 else 1.0
        else:
            oi_mom = 1.0
        
        oi_mom_list.append(oi_mom)
        skew_list.append(curr_skew)
    
    df['option_oi'] = [opt_metrics_map.get(t, (0, 0.7))[0] for t in df['ticker']]
    df['pct_oi_mom'] = pd.Series(oi_mom_list).rank(pct=True) * 100
    df['pct_skew'] = (1 - pd.Series(skew_list).rank(pct=True)) * 100

    # 3. Yapisal ve Insider Birlestir
    df = df.merge(df_yapisal[['ticker', 'squeeze_skor']], on='ticker', how='left')
    df['squeeze_skor'] = df['squeeze_skor'].fillna(50.0)
    df['insider_bonus'] = df['ticker'].map(insider_bonus_map).fillna(0)

    # 4. Final Skor (Adaptif Kurumsal Agirliklar)
    df['quant_score'] = (
        ((df['vol_z'] * 10 + 50) * 0.25) +
        (df['squeeze_skor'] * 0.25) +
        (df['pct_oi_mom'] * 0.25) +
        (df['pct_skew'] * 0.25) +
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
