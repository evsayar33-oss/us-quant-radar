import numpy as np
import pandas as pd
import yfinance as yf
import os

GECMIS_DOSYA = "gecmis_veri.csv"
MOM_PENCERE = 5 

def gunluk_veri_cek(tickers):
    """
    1 Yıllık veriyi çeker. Sadece aşırı çöp hisseleri (Fiyat < $3, Hacim yok) eler.
    Diğer tüm hisseleri tutar ancak aşağıda puanlama ile testere olanları dibe batırır.
    """
    try:
        if not tickers:
            return pd.DataFrame()

        # 1 Yıllık veriyi toplu indir
        data = yf.download(tickers, period="1y", interval="1d", progress=False, group_by='column')
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
                    
                    # Sadece mutlak çöpleri at ($3 altı ve hacimsizler)
                    dollar_volume = close_today * vol_today
                    if close_today < 3.0 or dollar_volume < 2_000_000:
                        continue

                    # Çoklu Zaman Dilimi Getirileri (1 Yıllık, 6 Aylık, 3 Aylık, 1 Aylık, 5 Günlük)
                    mom_1y = float((close_today / p_series.iloc[0] - 1) * 100)
                    mom_6mo = float((close_today / p_series.iloc[-126] - 1) * 100) if len(p_series) >= 126 else mom_1y
                    mom_3mo = float((close_today / p_series.iloc[-63] - 1) * 100) if len(p_series) >= 63 else mom_6mo
                    mom_1mo = float((close_today / p_series.iloc[-21] - 1) * 100) if len(p_series) >= 21 else mom_3mo
                    mom_5d = float((close_today / p_series.iloc[-5] - 1) * 100)

                    # 52 Haftalık Zirveye Uzaklık
                    high_52w = float(p_series.max())
                    dist_from_high = (close_today / high_52w - 1) * 100

                    # Trend Temizliği (R-Squared)
                    p_126 = p_series.tail(126)
                    y = np.log(p_126.values)
                    x = np.arange(len(y))
                    slope, intercept = np.polyfit(x, y, 1)
                    y_pred = slope * x + intercept
                    ss_res = np.sum((y - y_pred) ** 2)
                    ss_tot = np.sum((y - np.mean(y)) ** 2)
                    r_squared = 1 - (ss_res / (ss_tot + 1e-9))

                    # RVOL (Göreceli Hacim)
                    hist_vol = v_series.iloc[:-1].tail(20)
                    vol_avg = float(hist_vol.mean())
                    rvol = vol_today / (vol_avg + 1e-9) if vol_avg > 0 else 1.0

                    vol_3d_avg = float(v_series.iloc[-4:-1].mean()) if len(v_series) >= 4 else vol_avg
                    vol_accel = vol_today / (vol_3d_avg + 1e-9) if vol_3d_avg > 0 else 1.0

                    high_today = float(h_series.iloc[-1])
                    low_today = float(l_series.iloc[-1])
                    candle_range = high_today - low_today
                    close_strength = (close_today - low_today) / (candle_range + 1e-9) if candle_range > 0 else 0.7

                    df_bugun.append({
                        "ticker": t,
                        "close": round(close_today, 2),
                        "volume": vol_today,
                        "change_%": round(change_pct, 2),
                        "rvol": round(rvol, 2),
                        "vol_accel": round(vol_accel, 2),
                        "mom_5d": round(mom_5d, 2),
                        "mom_1mo": round(mom_1mo, 2),
                        "mom_3mo": round(mom_3mo, 2),
                        "mom_6mo": round(mom_6mo, 2),
                        "mom_1y": round(mom_1y, 2),
                        "dist_high": round(dist_from_high, 2),
                        "close_strength": round(close_strength, 2),
                        "trend_purity": round(float(r_squared), 2)
                    })
                    
        return pd.DataFrame(df_bugun)
    except Exception as e:
        print(f"Veri cekme hatasi: {e}")
        return pd.DataFrame()

def get_advanced_option_metrics(ticker):
    return 1.0, 0.7

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map, opt_metrics_map):
    """
    Sert silme (continue) yerine 'Ceza Puanı (Soft Penalty)' sistemi kullanır.
    Yatay / Testere hisselerin puanı %70 kesilerek dibe batırılır; 
    1 yıllık getirisi yüksek gerçek liderler zirvede tutulur.
    """
    if df.empty: 
        return df

    if 'rvol' not in df.columns: df['rvol'] = 1.0
    if 'vol_accel' not in df.columns: df['vol_accel'] = 1.0
    if 'close_strength' not in df.columns: df['close_strength'] = 0.7
    if 'trend_purity' not in df.columns: df['trend_purity'] = 0.5
    if 'mom_5d' not in df.columns: df['mom_5d'] = df['change_%']
    if 'mom_1mo' not in df.columns: df['mom_1mo'] = 0.0
    if 'mom_3mo' not in df.columns: df['mom_3mo'] = 0.0
    if 'mom_6mo' not in df.columns: df['mom_6mo'] = 0.0
    if 'mom_1y' not in df.columns: df['mom_1y'] = 0.0
    if 'dist_high' not in df.columns: df['dist_high'] = -20.0

    df['rvol_ratio'] = df['rvol']
    df['option_oi'] = df['rvol']

    # 1. Hacim Gücü Skoru (0 - 100)
    rvol_score = np.clip(((df['rvol'] - 0.5) / 2.5 * 60) + ((df['vol_accel'] - 0.5) / 2.0 * 40), 10, 100)

    # 2. Uzun Vadeli Bileşik Momentum Skoru (0 - 100) - 1 Yıllık Getiriye Büyük Ağırlık!
    mom_score = np.clip(
        30 + 
        (df['mom_1y'] * 0.3) + 
        (df['mom_6mo'] * 0.2) + 
        (df['mom_3mo'] * 0.2) + 
        (df['change_%'] * 1.5), 
        0, 100
    )

    # 3. TESTERE VE YATAY PİYASA CEZA ÇARPANI (Soft Penalty)
    trend_multiplier = []
    for _, row in df.iterrows():
        mult = 1.0
        
        # TESTERE FİLTRESİ: 1 yıllık getirisi %15'in altında olan (yerinde sayan A, BBY, ESS gibi) hisselere ağır ceza!
        if row['mom_1y'] < 15.0:
            mult *= 0.30  # Puanı %70 kırıp dibe batırır
        elif row['mom_1y'] > 40.0:
            mult *= 1.30  # Gerçek uzun vadeli süper trend liderlerine büyük bonus

        # Zikzak (R-squared) düşükse ceza
        if row['trend_purity'] < 0.45:
            mult *= 0.50

        # Zirveden çok uzaksa ceza
        if row['dist_high'] < -25.0:
            mult *= 0.60
        elif row['dist_high'] >= -8.0:
            mult *= 1.20 # Yeni ATH / Zirve kırılımı bonusu

        # Kapanış gücü
        if row['close_strength'] < 0.40:
            mult *= 0.70
        elif row['close_strength'] >= 0.75:
            mult *= 1.10

        # Günlük eksi kapatanlar
        if row['change_%'] < 0:
            mult *= 0.40

        trend_multiplier.append(mult)

    quality_factor = np.array(trend_multiplier)

    # 4. Göstergeler (Telegram ve Streamlit)
    df['pct_oi_mom'] = mom_score.round(1)
    df['pct_skew'] = (df['mom_1y']).round(1) # Skew alanında artık 1 yıllık net getiri %'si yazar

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
    base_score = (rvol_score * 0.25) + (mom_score * 0.50) + (df['squeeze_skor'] * 0.25)
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
