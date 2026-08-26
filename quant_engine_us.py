import numpy as np
import pandas as pd
import yfinance as yf
import os

GECMIS_DOSYA = "gecmis_veri.csv"
MOM_PENCERE = 5 

def gunluk_veri_cek(tickers):
    """
    Düşük arzlı ve yüksek momentumlu hisselerin son 1 aylık 
    fiyat/hacim verilerini tek seferde toplu çeker.
    RVOL (Hacim Patlaması) ve Kırılım Momentumunu hesaplar.
    """
    try:
        if not tickers:
            return pd.DataFrame()

        # Tek toplu istek (Rate-limit yemez, hızlı ve güvenilirdir)
        data = yf.download(tickers, period="1mo", interval="1d", progress=False, group_by='column')
        if data.empty:
            return pd.DataFrame()

        # MultiIndex ve tekli sütun yapısını güvenli çöz
        if isinstance(data.columns, pd.MultiIndex):
            closes = data['Close'].ffill() if 'Close' in data.columns.levels[0] else pd.DataFrame()
            volumes = data['Volume'].ffill() if 'Volume' in data.columns.levels[0] else pd.DataFrame()
        else:
            if 'Close' in data.columns:
                first_t = tickers[0] if isinstance(tickers, list) else tickers
                closes = pd.DataFrame({first_t: data['Close'].ffill()})
                volumes = pd.DataFrame({first_t: data['Volume'].ffill()})
            else:
                return pd.DataFrame()

        df_bugun = []
        for t in tickers:
            if t in closes.columns and t in volumes.columns:
                p_series = closes[t].dropna()
                v_series = volumes[t].dropna()
                
                if len(p_series) >= 2 and len(v_series) >= 2:
                    close_today = float(p_series.iloc[-1])
                    close_prev = float(p_series.iloc[-2])
                    change_pct = float((close_today / close_prev - 1) * 100)
                    
                    vol_today = float(v_series.iloc[-1])
                    
                    # 20 günlük taban hacim ve standart sapma hesabı
                    if len(v_series) >= 5:
                        hist_vol = v_series.iloc[:-1].tail(20) if len(v_series) > 5 else v_series
                        vol_avg = float(hist_vol.mean())
                        vol_std = float(hist_vol.std()) if len(hist_vol) > 1 else 1.0
                    else:
                        vol_avg = float(v_series.mean())
                        vol_std = 1.0

                    # RVOL: Bugünkü Hacim / 20 Günlük Ortalama (Arzı az hisseye giren anormal para akışı)
                    rvol = vol_today / (vol_avg + 1e-9) if vol_avg > 0 else 1.0
                    
                    # Hacim Z-Skoru (-3 ile +3 arası)
                    vol_z = (vol_today - vol_avg) / (vol_std + 1e-9) if vol_std > 0 else 0.0
                    vol_z = float(np.clip(vol_z, -3, 3))
                    
                    # 5 Günlük İvme ve Kırılım
                    if len(p_series) >= 5:
                        mom_5d = float((close_today / p_series.iloc[-5] - 1) * 100)
                    else:
                        mom_5d = change_pct

                    df_bugun.append({
                        "ticker": t,
                        "close": round(close_today, 2),
                        "volume": vol_today,
                        "change_%": round(change_pct, 2),
                        "rvol": round(rvol, 2),
                        "vol_z": round(vol_z, 2),
                        "mom_5d": round(mom_5d, 2)
                    })
                    
        return pd.DataFrame(df_bugun)
    except Exception as e:
        print(f"Veri cekme hatasi: {e}")
        return pd.DataFrame()

def get_advanced_option_metrics(ticker):
    """GitHub Actions rate-limit engeli yememek için güvenli mock döner."""
    return 1.0, 0.7

def calculate_us_scores(df, df_gecmis, df_yapisal, insider_bonus_map, opt_metrics_map):
    """
    Düşük Arz + Yüksek RVOL + Short Squeeze + Alım Yönlü Kırılım
    mantığına göre hisseleri puanlar ve en patlamaya hazır hisseleri zirveye taşır.
    """
    if df.empty: 
        return df

    # 1. RVOL Güvencesi
    if 'rvol' not in df.columns:
        df['rvol'] = 1.0
    if 'vol_z' not in df.columns:
        df['vol_z'] = 0.0
        
    df['rvol_ratio'] = df['rvol']
    df['option_oi'] = df['rvol']

    # 2. Hacim Patlaması Skoru (RVOL Score: 0 - 100)
    # RVOL > 1.5 yükseliş alarmı, RVOL > 3.0 devasa kurumsal/perakende akınıdır
    rvol_score = np.clip((df['rvol'] - 0.5) / 2.5 * 100, 10, 100)

    # 3. Kırılım ve Momentum Skoru (0 - 100)
    # Fiyat yukarı koparken gelen hacim en yüksek puanı alır
    if 'mom_5d' in df.columns:
        mom_base = df['mom_5d']
    else:
        mom_base = df['change_%']
    
    mom_score = np.clip(50 + (df['change_%'] * 3.0) + (mom_base * 1.5), 0, 100)

    # Telegram ve Streamlit göstergeleri için dinamik yüzdeler
    df['pct_oi_mom'] = mom_score.round(1)
    df['pct_skew'] = rvol_score.round(1)

    # 4. Yapısal Squeeze ve Insider Verilerini Birleştir
    if df_yapisal is not None and not df_yapisal.empty and 'squeeze_skor' in df_yapisal.columns:
        df = df.merge(df_yapisal[['ticker', 'squeeze_skor']], on='ticker', how='left')
        df['squeeze_skor'] = df['squeeze_skor'].fillna(50.0)
    else:
        df['squeeze_skor'] = 50.0

    if insider_bonus_map:
        df['insider_bonus'] = df['ticker'].map(insider_bonus_map).fillna(0.0)
    else:
        df['insider_bonus'] = 0.0

    # 5. Yön Doğrulaması (DÜŞENLERİ ELEME FİLTRESİ):
    # Eğer hisse sert düşüyorsa (change_% < 0), hacim ALIM değil SATIŞ/BOŞALTMA hacmidir.
    # Düşen hisselere %40 ceza çarpanı uygulanır, böylece listede asla zirveye çıkamazlar!
    trend_filter = np.where(df['change_%'] < 0, 0.60, 1.0)

    # 6. Final Quant Skoru
    # Ağırlıklar: %40 RVOL Hacim Patlaması + %35 Fiyat Kırılım İvmesi + %25 Short Squeeze Potansiyeli
    raw_score = (rvol_score * 0.40) + (mom_score * 0.35) + (df['squeeze_skor'] * 0.25)
    final_score = (raw_score * trend_filter) + df['insider_bonus']
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
