import numpy as np
import pandas as pd
import yfinance as yf
import os

GECMIS_DOSYA = "gecmis_veri.csv"

def gunluk_veri_cek(tickers):
    """
    ÖNCÜ PATLAMA ÖNCESİ TOPLAMA AVCISI (Pre-Breakout Accumulation Hunter):
    - Çevik fonların işlem yapabileceği esnek likiditede ($3M+) çalışır.
    - Şok patlama GELMEDEN ÖNCE fonların mal toplama (Accumulation) ve sıkışma (Tightness/Coiling) izlerini sürer.
    """
    try:
        if not tickers:
            return pd.DataFrame()

        # 3 aylık veri konsolidasyon ve toplanma evresini yakalamak için idealdir
        data = yf.download(tickers, period="3mo", interval="1d", progress=False, group_by='column')
        if data.empty:
            return pd.DataFrame()

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
                
                if len(p_series) >= 30 and len(v_series) >= 30:
                    close_today = float(p_series.iloc[-1])
                    close_prev = float(p_series.iloc[-2])
                    change_pct = float((close_today / close_prev - 1) * 100)
                    vol_today = float(v_series.iloc[-1])
                    
                    # Çevik fon eşiği: $3+ fiyat ve günlük $3M+ hacim
                    dollar_volume = close_today * vol_today
                    if close_today < 3.0 or dollar_volume < 3_000_000:
                        continue

                    # 1. AKILLI PARA BİRİKİMİ (Accumulation Ratio): Son 20 günde yeşil gün hacimleri / kırmızı gün hacimleri
                    sub = pd.DataFrame({'close': p_series.tail(20), 'vol': v_series.tail(20)})
                    sub['ret'] = sub['close'].pct_change()
                    up_vol = sub[sub['ret'] > 0]['vol'].sum()
                    down_vol = sub[sub['ret'] < 0]['vol'].sum() + 1e-9
                    acc_ratio = float(up_vol / down_vol) 

                    # 2. VOLATİLİTE DARALMASI / SIKIŞMA (VCP / Coiling): Son 10 günlük ATR / 30 günlük ATR oranı
                    tr = np.maximum(h_series - l_series, np.abs(h_series - closes.shift(1)))
                    atr_10 = tr.tail(10).mean()
                    atr_30 = tr.tail(30).mean() + 1e-9
                    tightness = float(atr_10 / atr_30)

                    # 3. ZİRVE KONSOLİDASYONU: Hisse tabanda değil, 3 aylık aralığın üst yarısında toplanıyor mu?
                    high_3mo = float(p_series.max())
                    low_3mo = float(p_series.min())
                    range_3mo = high_3mo - low_3mo
                    position = (close_today - low_3mo) / (range_3mo + 1e-9) if range_3mo > 0 else 0.5

                    if position < 0.35:
                        continue

                    df_bugun.append({
                        "ticker": t,
                        "close": round(close_today, 2),
                        "volume": vol_today,
                        "change_%": round(change_pct, 2),
                        "acc_ratio": round(acc_ratio, 2),
                        "tightness": round(tightness, 2),
                        "position": round(position, 2)
                    })
                                
        return pd.DataFrame(df_bugun)
    except Exception as e:
        print(f"Veri cekme hatasi: {e}")
        return pd.DataFrame()

def get_advanced_option_metrics(ticker):
    return 1.0, 0.7

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map, opt_metrics_map):
    """
    Öncü Toplanma Skorlama Motoru:
    - Tüm Streamlit ve Telegram sütun gereksinimleri (rvol_ratio, option_oi vb.) tam uyumlu hale getirilmiştir.
    """
    if df.empty: 
        return df

    if 'acc_ratio' not in df.columns: df['acc_ratio'] = 1.0
    if 'tightness' not in df.columns: df['tightness'] = 1.0
    if 'position' not in df.columns: df['position'] = 0.5

    # Streamlit ve Telegram botunun aradığı yedek sütun köprüleri (Hata önleyici)
    df['rvol_ratio'] = df['acc_ratio']
    df['option_oi'] = df['tightness']

    if df_yapisal is not None and not df_yapisal.empty and 'squeeze_skor' in df_yapisal.columns:
        df = df.merge(df_yapisal[['ticker', 'squeeze_skor']], on='ticker', how='left')
        df['squeeze_skor'] = df['squeeze_skor'].fillna(50.0)
    else:
        df['squeeze_skor'] = 50.0

    if insider_bonus_map:
        df['insider_bonus'] = df['ticker'].map(insider_bonus_map).fillna(0.0)
    else:
        df['insider_bonus'] = 0.0

    # Normalizasyonlar
    acc_norm = np.clip((df['acc_ratio'] - 1.0) / 1.5 * 100, 10, 100)
    tight_norm = np.clip((1.2 - df['tightness']) / 0.6 * 100, 10, 100)
    pos_norm = np.clip(df['position'] * 100, 10, 100)
    squeeze_norm = np.clip(df['squeeze_skor'], 0, 100)

    quant_scores = []
    pct_oi_list = []
    pct_skew_list = []

    for i, row in df.iterrows():
        a_score = acc_norm.iloc[i]
        t_score = tight_norm.iloc[i]
        p_score = pos_norm.iloc[i]
        s_score = squeeze_norm.iloc[i]
        bonus = row['insider_bonus']
        chg = row['change_%']

        # Formül: %35 Mal Toplama + %30 Volatilite Sıkışması + %15 Zirve Konumu + %20 Squeeze
        score = (a_score * 0.35) + (t_score * 0.30) + (p_score * 0.15) + (s_score * 0.20) + bonus

        if chg < -3.0:
            score *= 0.70

        quant_scores.append(np.clip(score, 0, 100))
        pct_oi_list.append(a_score)
        pct_skew_list.append(t_score)

    df['quant_score'] = np.array(quant_scores).round(1)
    df['pct_oi_mom'] = np.array(pct_oi_list).round(1)
    df['pct_skew'] = np.array(pct_skew_list).round(1)

    # Skor Farkı Hesabı (Gecmis veri çakışmasını önleyen güvenli yapı)
    df['score_diff'] = 0.0
    if df_gecmis is not None and not df_gecmis.empty and 'quant_score' in df_gecmis.columns:
        if 'tarih' in df_gecmis.columns:
            son_tarih = df_gecmis['tarih'].max()
            df_son = df_gecmis[df_gecmis['tarih'] == son_tarih]
            eski_map = dict(zip(df_son['ticker'], df_son['quant_score']))
            df['score_diff'] = (df['quant_score'] - df['ticker'].map(eski_map).fillna(df['quant_score'])).round(1)

    return df.sort_values(by='quant_score', ascending=False).reset_index(drop=True)
