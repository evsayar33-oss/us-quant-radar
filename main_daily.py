import os
import pandas as pd
from datetime import datetime
import pytz
from universe import get_universe
from structural_gate import yapisal_gate_yukle
from insider_check import get_cik_map, check_insider_buys
from quant_engine_us import gunluk_veri_cek, calculate_us_scores, GECMIS_DOSYA

def run_daily():
    est = pytz.timezone('US/Eastern')
    bugun = datetime.now(est).strftime('%Y-%m-%d')
    
    tickers = get_universe()[:100] # Hizli test icin ilk 100, tumu icin silin
    df_bugun = gunluk_veri_cek(tickers)
    
    df_gecmis = pd.read_csv(GECMIS_DOSYA) if os.path.exists(GECMIS_DOSYA) else pd.DataFrame()
    df_yapisal = yapisal_gate_yukle()
    
    # Sadece ilk 20 hisse icin insider kontrolu (SEC limitleri icin)
    cik_map = get_cik_map()
    insider_bonus_map = {}
    for t in tickers[:20]:
        if t in cik_map:
            insider_bonus_map[t] = check_insider_buys(t, cik_map[t])

    df_final = calculate_us_scores(df_bugun, df_gecmis, df_yapisal, insider_bonus_map)
    df_final.to_csv("sonuclar.csv", index=False)
    
    # Kayit
    df_bugun['tarih'] = bugun
    df_bugun.to_csv(GECMIS_DOSYA, mode='a', header=not os.path.exists(GECMIS_DOSYA), index=False)

if __name__ == "__main__":
    run_daily()
