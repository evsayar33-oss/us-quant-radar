import numpy as np
import pandas as pd
import yfinance as yf
import os

GECMIS_DOSYA = "gecmis_veri.csv"
MOM_PENCERE = 5 

def gunluk_veri_cek(tickers):
    """
    3 Aylık (60 Günlük) makro trendi çeker.
    Genel grafiği düşüş trendinde olan (CAN, BEAM vb.) hisseleri tespit edip eler.
    """
    try:
        if not tickers:
            return pd.DataFrame()

        # 3 aylık veriyi tek toplu istekte çekiyoruz (Orta vadeli gerçek trendi görmek için)
        data = yf.download(tickers, period="3mo", interval="1d", progress=False, group_by='column')
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
                
                if len(p_series) >= 20 and len(v_series) >= 20:
                    close_today = float(p_series.iloc[-1])
                    close_prev = float(p_series.iloc[-2])
                    change_pct = float((close_today / close_prev - 1) * 100)
                    
                    vol_today = float(v_series.iloc[-1])
                    
                    # 1. 20 Günlük Hacim Ortalaması ve RVOL
                    hist_vol = v_series.iloc[:-1].tail(20)
                    vol_avg = float(hist_vol.mean())
                    vol_std = float(hist_vol.std()) if len(hist_vol) > 1 else 1.0
                    rvol = vol_today / (vol_avg + 1e-9) if vol_avg > 0 else 1.0
                    vol_z = float(np.clip((vol_today - vol_avg) / (vol_std + 1e-9), -3, 3))
                    
                    # 2. Hacim İvmesi (Son 3 gün ortalamasına göre)
                    vol_3d_avg = float(v_series.iloc[-4:-1].mean()) if len(v_series) >= 4 else vol_avg
                    vol_accel = vol_today / (vol_3d_avg + 1e-9) if vol_3d_avg > 0 else 1.0

                    # 3. Kapanış Gücü (Günün en tepesine yakın kapatma)
                    high_today = float(h_series.iloc[-1])
                    low_today = float(l_series.iloc[-1])
                    candle_range = high_today - low_today
                    close_strength = (close_today - low_today) / (candle_range + 1e-9) if candle_range > 0 else 0.7

                    # 4. Kısa ve Orta Vade İvmeler
                    mom_3d = float((close_today / p_series.iloc[-3] - 1) * 100)
                    mom_5d = float((close_today / p_series.iloc[-5] - 1) * 100)
                    mom_1mo = float((close_today / p_series.iloc[-20] - 1) * 100) # 1 Aylık Değişim
                    mom_3mo = float((close_today / p_series.iloc[0] - 1) * 100)   # 3 Aylık Makro Trend

                    # 5. 3 AYLIK MAKRO ZİRVE / DİP POZİSYONU (Macro Trend Range)
                    high_3mo = float(p_series.max())
                    low_3mo = float(p_series.min())
                    range_3mo = high_3mo - low_3mo
                    macro_position = (close_today - low_3mo) / (range_3mo + 1e-9) if range_3mo > 0 else 0.5

                    df_bugun.append({
                        "ticker": t,
                        "close": round(close_today, 2),
                        "volume": vol_today,
                        "change_%": round(change_pct, 2),
                        "rvol": round(rvol, 2),
                        "vol_z": round(vol_z, 2),
                        "vol_accel": round(vol_accel, 2),
                        "mom_3d": round(mom_3d, 2),
                        "mom_5d": round(mom_5d, 2),
                        "mom_1mo": round(mom_1mo, 2),
                        "mom_3mo": round(mom_3mo, 2),
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
    Sadece 3 aylık makro trendi güçlü olan hisseleri listeler;
    düşüş trendindeki sahte zıplamaları (CAN, BEAM vb.) tamamen eler.
    """
    if df.empty: 
        return df

    if 'rvol' not in df.columns: df['rvol'] = 1.0
    if 'vol_z' not in df.columns: df['vol_z'] = 0.0
    if 'vol_accel' not in df.columns: df['vol_accel'] = 1.0
    if 'close_strength' not in df.columns: df['close_strength'] = 0.7
    if 'mom_3d' not in df.columns: df['mom_3d'] = df['change_%']
    if 'mom_5d' not in df.columns: df['mom_5d'] = df['change_%']
    if 'mom_1mo' not in df.columns: df['mom_1mo'] = 0.0
    if 'mom_3mo' not in df.columns: df['mom_3mo'] = 0.0
    if 'macro_position' not in df.columns: df['macro_position'] = 0.5

    df['rvol_ratio'] = df['rvol']
    df['option_oi'] = df['rvol']

    # 1. Hacim Gücü Skoru (0 - 100)
    rvol_score = np.clip(((df['rvol'] - 0.5) / 2.5 * 60) + ((df['vol_accel'] - 0.5) / 2.0 * 40), 10, 100)

    # 2. Çoklu Momentum Skoru (0 - 100)
    mom_score = np.clip(50 + (df['change_%'] * 2.0) + (df['mom_3d'] * 1.5) + (df['mom_5d'] * 1.0) + (df['mom_1mo'] * 0.5), 0, 100)

    # 3. KESİN DÜŞÜŞ TRENDİ ELİYİCİ (Macro Trend Filter)
    trend_multiplier = []
    for _, row in df.iterrows():
        mult = 1.0
        
        # KURAL A: 3 Aylık trendi eksideyse veya 3 aylık dipte sürünüyorsa (CAN, BEAM Elenir)
        if row['mom_3mo'] < -10.0 or row['macro_position'] < 0.40:
            mult *= 0.20  # Puanı %80 kır (Doğrudan liste dışı kalır)
        elif row['mom_3mo'] > 15.0 and row['macro_position'] >= 0.70:
            mult *= 1.25  # Gerçekten yükselen trend liderlerine büyük bonus

        # KURAL B: 1 Aylık trendi eksideyse
        if row['mom_1mo'] < 0:
            mult *= 0.50

        # KURAL C: Günün en tepesinden satış yediyse
        if row['close_strength'] < 0.40:
            mult *= 0.60
        elif row['close_strength'] >= 0.75:
            mult *= 1.10

        # KURAL D: Günlük eksi kapattıysa
        if row['change_%'] < 0:
            mult *= 0.30

        trend_multiplier.append(mult)

    quality_factor = np.array(trend_multiplier)

    # 4. Göstergeler (Telegram ve Streamlit)
    df['pct_oi_mom'] = mom_score.round(1)
    df['pct_skew'] = (df['macro_position'] * 100).round(1)  # Skew sütunu artık '3 Aylık Trend Gücü %'yi gösterir

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
    base_score = (rvol_score * 0.35) + (mom_score * 0.40) + (df['squeeze_skor'] * 0.25)
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
