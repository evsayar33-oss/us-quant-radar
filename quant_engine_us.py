import numpy as np
import pandas as pd
import yfinance as yf
import os

GECMIS_DOSYA = "gecmis_veri.csv"
MOM_PENCERE = 5 

def gunluk_veri_cek(tickers):
    """
    Tek günlük sahte hacim patlamalarını (Fakeout) elemek için;
    Hacmin sadece bugün değil, son 3-5 gündür de kalıcı olarak yüksek olup olmadığını (Persistence) ölçer.
    """
    try:
        if not tickers:
            return pd.DataFrame()

        # 6 aylık veriyi toplu indir
        data = yf.download(tickers, period="6mo", interval="1d", progress=False, group_by='column')
        if data.empty:
            return pd.DataFrame()

        # Sütunları güvenle ayıkla
        if isinstance(data.columns, pd.MultiIndex):
            closes = data['Close'].ffill() if 'Close' in data.columns.levels[0] else pd.DataFrame()
            volumes = data['Volume'].ffill() if 'Volume' in data.columns.levels[0] else pd.DataFrame()
            highs = data['High'].ffill() if 'High' in data.columns.levels[0] else pd.DataFrame()
            lows = data['Low'].ffill() if 'Low' in data.columns.levels[0] else pd.DataFrame()
        else:
            if 'Close' in data.columns:
                first_t = tickers[0] if isinstance(tickers, list) else tickers
                closes = pd.DataFrame({first_t: data['Close'].ffill()})
                volumes = pd.DataFrame({first_t: data['Volume'].ffill()})
                highs = pd.DataFrame({first_t: data['High'].ffill()})
                lows = pd.DataFrame({first_t: data['Low'].ffill()})
            else:
                return pd.DataFrame()

        df_bugun = []
        for t in tickers:
            if t in closes.columns and t in volumes.columns:
                p_series = closes[t].dropna()
                v_series = volumes[t].dropna()
                h_series = highs[t].dropna() if t in highs.columns else p_series
                l_series = lows[t].dropna() if t in lows.columns else p_series
                
                if len(p_series) >= 60 and len(v_series) >= 60:
                    close_today = float(p_series.iloc[-1])
                    close_prev = float(p_series.iloc[-2])
                    change_pct = float((close_today / close_prev - 1) * 100)
                    vol_today = float(v_series.iloc[-1])
                    
                    # Kuruşluk çöpleri ve sığ tahtaları ele ($5 altı ve $2M altı hacim)
                    dollar_volume = close_today * vol_today
                    if close_today < 5.0 or dollar_volume < 2_000_000:
                        continue

                    # 20 Günlük Ortalama Hacim Tabanı
                    hist_vol = v_series.iloc[:-1].tail(20)
                    vol_avg = float(hist_vol.mean())
                    if vol_avg <= 0: continue

                    # 1. RVOL (Bugünkü Hacim Patlaması)
                    rvol_today = vol_today / vol_avg

                    # 2. 3 GÜNLÜK HACİM KALICILIĞI (Multi-Day Volume Persistence): 
                    # Hacim sadece bugün mü patladı, yoksa son 3 gündür de yüksek mi?
                    vol_3d_avg = float(v_series.iloc[-3:].mean())
                    rvol_3d = vol_3d_avg / vol_avg

                    # Trend Kapısı (3 aylık getiri ve 6 aylık makro konum)
                    mom_3mo = float((close_today / p_series.iloc[-63] - 1) * 100) if len(p_series) >= 63 else 0.0
                    high_6mo = float(p_series.max())
                    low_6mo = float(p_series.min())
                    range_6mo = high_6mo - low_6mo
                    macro_position = (close_today - low_6mo) / (range_6mo + 1e-9) if range_6mo > 0 else 0.5

                    # Kötü trendlileri kapıdan at
                    if mom_3mo < -2.0 or macro_position < 0.45:
                        continue

                    # Sıkı Hacim Filtresi: Tek günlük sahte patlamaları (RVOL < 1.10 veya 3 günlük ortalaması düşük olanları) ele
                    if rvol_today < 1.10 or rvol_3d < 1.05:
                        continue

                    # Kapanış Gücü
                    high_today = float(h_series.iloc[-1])
                    low_today = float(l_series.iloc[-1])
                    candle_range = high_today - low_today
                    close_strength = (close_today - low_today) / (candle_range + 1e-9) if candle_range > 0 else 0.7

                    # İstikrarlı Çoklu Zaman İvmeleri (1G, 3G, 5G, 1A)
                    mom_3d = float((close_today / p_series.iloc[-3] - 1) * 100) if len(p_series) >= 3 else change_pct
                    mom_5d = float((close_today / p_series.iloc[-5] - 1) * 100) if len(p_series) >= 5 else change_pct
                    mom_1mo = float((close_today / p_series.iloc[-20] - 1) * 100) if len(p_series) >= 20 else change_pct

                    df_bugun.append({
                        "ticker": t,
                        "close": round(close_today, 2),
                        "volume": vol_today,
                        "change_%": round(change_pct, 2),
                        "rvol": round(rvol_today, 2),
                        "rvol_3d": round(rvol_3d, 2),
                        "mom_3d": round(mom_3d, 2),
                        "mom_5d": round(mom_5d, 2),
                        "mom_1mo": round(mom_1mo, 2),
                        "close_strength": round(close_strength, 2),
                        "macro_position": round(macro_position, 2)
                    })
                    
        return pd.DataFrame(df_bugun)
    except Exception as e:
        print(f"Veri cekme hatasi: {e}")
        return pd.DataFrame()

def get_advanced_option_metrics(ticker):
    return 1.0, 0.7

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map, opt_metrics_map):
    """
    Hacmin sürekliliğine (Persistence) ve istikrarlı basamak ivmesine göre puanlar.
    Tek günlük hacim tuzaklarını en alta atar.
    """
    if df.empty: 
        return df

    if 'rvol' not in df.columns: df['rvol'] = 1.0
    if 'rvol_3d' not in df.columns: df['rvol_3d'] = 1.0
    if 'close_strength' not in df.columns: df['close_strength'] = 0.7
    if 'mom_3d' not in df.columns: df['mom_3d'] = df['change_%']
    if 'mom_5d' not in df.columns: df['mom_5d'] = df['change_%']
    if 'mom_1mo' not in df.columns: df['mom_1mo'] = 0.0
    if 'macro_position' not in df.columns: df['macro_position'] = 0.5

    df['rvol_ratio'] = df['rvol']
    df['option_oi'] = df['rvol']

    # 1. Hacim Kalıcılık Skoru (Bugünkü RVOL + Son 3 Günlük RVOL Ortalaması)
    persistence_score = np.clip(((df['rvol'] - 1.0) / 3.0 * 50) + ((df['rvol_3d'] - 1.0) / 2.0 * 50), 10, 100)

    # 2. İstikrarlı Basamak İvme Skoru (1G, 3G, 5G, 1A pozitif uyum)
    mom_score = np.clip(
        40 + 
        (df['change_%'] * 2.0) + 
        (df['mom_3d'] * 1.5) + 
        (df['mom_5d'] * 1.0) + 
        (df['mom_1mo'] * 0.5), 
        0, 100
    )

    # 3. DEVAMLILIK ÇARPANI (Continuation Multiplier)
    continuation_mult = []
    for _, row in df.iterrows():
        mult = 1.0
        
        # Eğer hacim hem bugün hem de son 3 gündür ortalamanın çok üzerindeyse (Gerçek Akümülasyon)
        if row['rvol'] >= 2.0 and row['rvol_3d'] >= 1.5:
            mult *= 1.35
        # Eğer sadece bugün patlayıp dün hacimsizse (Tek günlük şüphe / Fakeout)
        elif row['rvol'] >= 2.0 and row['rvol_3d'] < 1.2:
            mult *= 0.75 # Cezalandırılır

        # Trend ne kadar güçlüyse
        if row['macro_position'] >= 0.75:
            mult *= 1.20

        # Kapanış gücü
        if row['close_strength'] >= 0.80:
            mult *= 1.15
        elif row['close_strength'] < 0.40:
            mult *= 0.50

        # Günlük eksi kapatanlar
        if row['change_%'] < 0:
            mult *= 0.10

        continuation_mult.append(mult)

    quality_factor = np.array(continuation_mult)

    # 4. Göstergeler (Telegram ve Streamlit)
    df['pct_oi_mom'] = mom_score.round(1)
    df['pct_skew'] = (df['rvol_3d'] * 50).round(1) # Skew alanında '3 Günlük Ortalama Hacim Çarpanı' yazar

    # 5. Squeeze ve Insider Verileri
    if df_yapisal is not None and not df_yapisal.empty and 'squeeze_skor' in df_yapisal.columns:
        df = df.merge(df_yapisal[['ticker', 'squeeze_skor']], on='ticker', how='left')
        df['squeeze_skor'] = df['squeeze_skor'].fillna(50.0)
    else:
        df['squeeze_skor'] = 50.0

    if insider_bonus_map:
        df['insider_bonus'] = df['ticker'].map(insider_bonus_map).fillna(0.0)
    else:
        df['insider_bonus'] = 0.0

    # 6. Final Quant Skoru
    base_score = (persistence_score * 0.40) + (mom_score * 0.35) + (df['squeeze_skor'] * 0.25)
    final_score = (base_score * quality_factor) + df['insider_bonus']
    df['quant_score'] = np.clip(final_score, 0, 100).round(1)

    # 7. Skor Farkı Hesabı
    df['score_diff'] = 0.0
    if df_gecmis is not None and not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        if 'tarih' in df_gecmis.columns:
            son_tarih = df_gecmis['tarih'].max()
            df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
            eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
            df['score_diff'] = (df['quant_score'] - df['ticker'].map(eski_map).fillna(df['quant_score'])).round(1)

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
