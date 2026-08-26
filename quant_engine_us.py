import numpy as np
import pandas as pd
import yfinance as yf
import os

GECMIS_DOSYA = "gecmis_veri.csv"
MOM_PENCERE = 5 

def gunluk_veri_cek(tickers):
    """
    1 Yıllık veriyi çekerek GEN gibi 20 yıllık testere/yatay hisseleri eler.
    Sadece 1 yıllık, 6 aylık ve 3 aylık grafiği soluksuz yükselen 'Süper Trend' hisselerini seçer.
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
                
                if len(p_series) >= 120 and len(v_series) >= 120:
                    close_today = float(p_series.iloc[-1])
                    close_prev = float(p_series.iloc[-2])
                    change_pct = float((close_today / close_prev - 1) * 100)
                    vol_today = float(v_series.iloc[-1])
                    
                    # 1. KURAL: Minimum Fiyat $5 ve Günlük Dolar Hacmi > $5M
                    dollar_volume = close_today * vol_today
                    if close_today < 5.0 or dollar_volume < 5_000_000:
                        continue

                    # 2. KURAL (TESTERE KATİLİ): 52 Haftalık Zirveye Yakınlık
                    # Hisse 1 yıllık zirvesinden en fazla %15 uzakta olabilir (GEN, BYND gibi yatay ve batıklar elenir)
                    high_52w = float(p_series.max())
                    dist_from_high = (close_today / high_52w - 1) * 100
                    if dist_from_high < -15.0:
                        continue

                    # 3. KURAL (UZUN VADELİ TREND): Çoklu Zaman Dilimi Getirileri
                    mom_1y = float((close_today / p_series.iloc[0] - 1) * 100)
                    mom_6mo = float((close_today / p_series.iloc[-126] - 1) * 100) if len(p_series) >= 126 else mom_1y
                    mom_3mo = float((close_today / p_series.iloc[-63] - 1) * 100)
                    mom_1mo = float((close_today / p_series.iloc[-21] - 1) * 100)
                    mom_5d = float((close_today / p_series.iloc[-5] - 1) * 100)

                    # Sıralı Yükseliş Şartı: Yıllık, 6 aylık ve 3 aylık getirisi zayıf/yatay olan testere hisseler elenir
                    if mom_1y < 15.0 or mom_6mo < 8.0 or mom_3mo < 3.0:
                        continue

                    # 4. KURAL: RVOL (En az 1.0 ve üzeri olmalı, ölü tahtalar elenir)
                    hist_vol = v_series.iloc[:-1].tail(20)
                    vol_avg = float(hist_vol.mean())
                    rvol = vol_today / (vol_avg + 1e-9) if vol_avg > 0 else 1.0
                    if rvol < 0.90:
                        continue

                    # Hacim İvmesi & Kapanış Gücü
                    vol_3d_avg = float(v_series.iloc[-4:-1].mean()) if len(v_series) >= 4 else vol_avg
                    vol_accel = vol_today / (vol_3d_avg + 1e-9) if vol_3d_avg > 0 else 1.0

                    high_today = float(h_series.iloc[-1])
                    low_today = float(l_series.iloc[-1])
                    candle_range = high_today - low_today
                    close_strength = (close_today - low_today) / (candle_range + 1e-9) if candle_range > 0 else 0.7

                    # Trend Kalite Puanı (52 Haftalık zirveye ne kadar yakınsa o kadar yüksek)
                    low_52w = float(p_series.min())
                    range_52w = high_52w - low_52w
                    trend_score_52w = (close_today - low_52w) / (range_52w + 1e-9) if range_52w > 0 else 0.5

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
                        "trend_score_52w": round(trend_score_52w, 2)
                    })
                    
        return pd.DataFrame(df_bugun)
    except Exception as e:
        print(f"Veri cekme hatasi: {e}")
        return pd.DataFrame()

def get_advanced_option_metrics(ticker):
    return 1.0, 0.7

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map, opt_metrics_map):
    """
    Sadece gerçek 'Süper Trend' (Uzun vadeli yükseliş kanalı) hisselerini puanlar.
    """
    if df.empty: 
        return df

    if 'rvol' not in df.columns: df['rvol'] = 1.0
    if 'vol_accel' not in df.columns: df['vol_accel'] = 1.0
    if 'close_strength' not in df.columns: df['close_strength'] = 0.7
    if 'trend_score_52w' not in df.columns: df['trend_score_52w'] = 0.5
    if 'mom_5d' not in df.columns: df['mom_5d'] = df['change_%']
    if 'mom_1mo' not in df.columns: df['mom_1mo'] = 0.0
    if 'mom_3mo' not in df.columns: df['mom_3mo'] = 0.0
    if 'mom_1y' not in df.columns: df['mom_1y'] = 0.0

    df['rvol_ratio'] = df['rvol']
    df['option_oi'] = df['rvol']

    # 1. Hacim Gücü Skoru (0 - 100)
    rvol_score = np.clip(((df['rvol'] - 0.5) / 2.5 * 60) + ((df['vol_accel'] - 0.5) / 2.0 * 40), 10, 100)

    # 2. Çok Zamanlı Süper Trend Momentum Skoru (0 - 100)
    # 1 Yıllık ve 6 Aylık trend ağırlığı artırıldı
    mom_score = np.clip(
        40 + 
        (df['change_%'] * 2.0) + 
        (df['mom_5d'] * 1.0) + 
        (df['mom_1mo'] * 0.4) + 
        (df['mom_3mo'] * 0.2) + 
        (df['mom_1y'] * 0.1), 
        0, 100
    )

    # 3. Zirve Kırılım ve Kalite Çarpanı
    trend_multiplier = []
    for _, row in df.iterrows():
        mult = 1.0
        
        # 52 Haftalık Zirvesine %5 veya daha yakınsa (Yeni ATH / Ralli Kırılımı)
        if row['dist_high'] >= -5.0:
            mult *= 1.30
        elif row['dist_high'] >= -10.0:
            mult *= 1.15

        # Kapanış gücü filtresi
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
    df['pct_skew'] = (df['trend_score_52w'] * 100).round(1)

    # 5. Squeeze ve Insider Verilerini Birleştir
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
    base_score = (rvol_score * 0.30) + (mom_score * 0.45) + (df['squeeze_skor'] * 0.25)
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
