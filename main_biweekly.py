import os
import pandas as pd
from datetime import datetime, timedelta
from universe import get_universe
from quant_engine_us import GECMIS_DOSYA
from structural_gate import yapisal_gate_hesapla

def get_last_settlement_date():
    """FINRA takvimine göre yaklaşık son settlement tarihini hesaplar."""
    # FINRA verileri genellikle ayın 15'i ve ay sonu gelir.
    # Bugünün tarihinden 10 gün geriye gidip en yakın 15 veya 30'u bulalım.
    today = datetime.now()
    check_date = today - timedelta(days=10)
    
    if check_date.day >= 15:
        # Ayın 15'i
        return check_date.replace(day=15).strftime('%Y-%m-%d')
    else:
        # Bir önceki ayın son günü
        last_day_prev_month = today.replace(day=1) - timedelta(days=1)
        return last_day_prev_month.strftime('%Y-%m-%d')

def run_biweekly():
    print("--- Yapısal Kapı Güncellemesi Başladı ---")
    
    # 1. Evreni ve Geçmişi Yükle
    tickers = get_universe()[:250] # Limit: 250 hisse
    df_gecmis = pd.read_csv(GECMIS_DOSYA) if os.path.exists(GECMIS_DOSYA) else pd.DataFrame()
    
    if df_gecmis.empty:
        print("Uyarı: Geçmiş veri yok, Days-to-Cover hesaplanamayabilir.")

    # 2. Settlement Tarihini Belirle
    # Not: FINRA API kullanıyorsan bu tarih kritik, yfinance fallback'te genel veri çekilir.
    settlement_date = get_last_settlement_date()
    
    # 3. Hesaplamayı Başlat
    print(f"Hesaplanıyor... Hedef Tarih: {settlement_date}")
    df_yapisal = yapisal_gate_hesapla(tickers, df_gecmis)
    
    if not df_yapisal.empty:
        print(f"Başarılı! {len(df_yapisal)} hisse için yapisal_gate.csv güncellendi.")
    else:
        print("Hata: Yapısal skorlar üretilemedi.")

if __name__ == "__main__":
    run_biweekly()
