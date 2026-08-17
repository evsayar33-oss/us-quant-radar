import numpy as np
import pandas as pd

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map):
    if df.empty: return df

    # 1. RVOL
    rvol_list = []
    for _, row in df.iterrows():
        gecmis = df_gecmis[df_gecmis['ticker'] == row['ticker']]['volume'].tail(20) if not df_gecmis.empty else []
        rvol = row['volume'] / gecmis.mean() if len(gecmis) >= 5 else 1.0
        rvol_list.append(rvol)
    df['rvol_ratio'] = rvol_list
    
    # 2. Yuzdelik Dilimler
    df['pct_rvol'] = df['rvol_ratio'].rank(pct=True) * 100
    df['pct_change'] = df['change_%'].rank(pct=True) * 100
    
    # 3. Yapisal Kapi
    df = df.merge(df_yapisal[['ticker', 'yapisal_skor']], on='ticker', how='left')
    df['yapisal_skor'] = df['yapisal_skor'].fillna(50.0)
    
    # 4. Insider Bonus
    df['insider_bonus'] = df['ticker'].map(insider_bonus_map).fillna(0)
    
    # 5. Skor
    df['quant_score'] = (df['pct_rvol'] * 0.40) + (df['pct_change'] * 0.25) + (df['yapisal_skor'] * 0.25) + df['insider_bonus']

    # 6. SKOR FARKI HESAPLA (ÇIKIŞ İÇİN)
    df['score_diff'] = 0.0
    if not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        son_tarih = df_gecmis['tarih'].max()
        df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
        eski_skor_map = dict(zip(df_son['ticker'], df_son['quant_score']))
        df['score_diff'] = df['quant_score'] - df['ticker'].map(eski_skor_map).fillna(df['quant_score'])

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
