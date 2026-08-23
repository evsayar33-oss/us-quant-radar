import numpy as np
import pandas as pd
import yfinance as yf
import os

GECMIS_DOSYA = "gecmis_veri.csv"
N_GUN = 5 # Momentum penceresi

def get_advanced_option_metrics(ticker):
    """Opsiyon OI Momentumu ve Skew verilerini ceker."""
    try:
        t = yf.Ticker(ticker)
        options = t.options
        if not options: return 0.0, 0.7 # OI_Mom, Skew_Proxy
        
        # En yakin 2 vadeyi al (hiz icin)
        total_puts_oi = 0
        total_calls_oi = 0
        
        for date in options[:2]:
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
        hist_v = df_gecmis[df_gecmis['ticker'] == row['ticker']]['volume'].tail(20) if not df_gecmis.empty else []
        z = (row['volume'] - hist_v.mean()) / (hist_v.std() + 1e-9) if len(hist_v) >= 5 else 0
        z_vol_list.append(np.clip(z, -3, 3))
    df['vol_z'] = z_vol_list

    # 2. OPSİYON OI MOMENTUMU VE SKEW RANK
    oi_mom_list, skew_list = [], []
    for _, row in df.iterrows():
        t = row['ticker']
        curr_oi, curr_skew = opt_metrics_map.get(t, (0.0, 0.7))
        
        # OI Momentum: Bugünkü OI / Gecmis OI Ortalamasi
        hist_oi = df_gecmis[df_gecmis['ticker'] == t]['option_oi'].tail(N_GUN) if not df_gecmis.empty else []
        oi_mom = curr_oi / hist_oi.mean() if len(hist_oi) >= 2 and hist_oi.mean() > 0 else 1.0
        
        oi_mom_list.append(oi_mom)
        skew_list.append(curr_skew)
    
    df['option_oi'] = [x[0] for x in opt_metrics_map.values()] if opt_metrics_map else 0.0
    df['pct_oi_mom'] = pd.Series(oi_mom_list).rank(pct=True) * 100
    df['pct_skew'] = (1 - pd.Series(skew_list).rank(pct=True)) * 100 # Dusuk skew (az Put) = Yuksek Puan

    # 3. SHORT VOLUME MOMENTUM (Yapisal Kapi uzerinden)
    df = df.merge(df_yapisal[['ticker', 'squeeze_skor', 'short_interest_%']], on='ticker', how='left')
    df['squeeze_skor'] = df['squeeze_skor'].fillna(50.0)

    # 4. FINAL KURUMSAL FORMUL (Agirliklar Söylediklerine Göre Güncellendi)
    # %25 RVOL + %25 Squeeze + %25 Opsiyon OI Mom + %25 Skew
    df['quant_score'] = (
        ((df['vol_z'] * 10 + 50) * 0.25) +
        (df['squeeze_skor'] * 0.25) +
        (df['pct_oi_mom'] * 0.25) +
        (df['pct_skew'] * 0.25) +
        df['ticker'].map(insider_bonus_map).fillna(0) # Insider Alim Dogrudan Bonus
    )

    # Skor Farkı
    df['score_diff'] = 0.0
    if not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        df_son = df_gecmis[df_gecmis['tarih'] == df_gecmis['tarih'].max()]
        eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        df['score_diff'] = df['quant_score'] - df['ticker'].map(eski_map).fillna(df['quant_score'])

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
