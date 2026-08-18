import os
import pandas as pd
import requests
import time
from datetime import datetime
import pytz
from universe import get_universe
from structural_gate import yapisal_gate_yukle
from insider_check import get_cik_map, check_insider_buys
from quant_engine_us import gunluk_veri_cek, calculate_us_scores, get_option_sentiment, GECMIS_DOSYA

def send_telegram_alert(df):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id: return
    top_10 = df.head(10)
    msg = "🇺🇸 *ADAPTIVE US QUANT LİDERLER*\n"
    for _, r in top_10.iterrows():
        # Dinamik durum tespiti: Piyasa geneline göre nerede?
        mood = "🔥" if r['pct_pc_rank'] > 80 else ("⚠️" if r['pct_pc_rank'] < 20 else "N")
        msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* | P/C Rank: %{r['pct_pc_rank']:.0f} {mood}\n"
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

def run_daily():
    est = pytz.timezone('US/Eastern')
    bugun = datetime.now(est).strftime('%Y-%m-%d')
    
    tickers = get_universe()[:250] 
    df_bugun = gunluk_veri_cek(tickers)
    if df_bugun.empty: return

    df_gecmis = pd.read_csv(GECMIS_DOSYA) if os.path.exists(GECMIS_DOSYA) else pd.DataFrame()
    df_yapisal = yapisal_gate_yukle()
    cik_map = get_cik_map()
    
    insider_bonus_map = {}
    option_data_map = {}
    
    # En iyi 40 adayı analiz et
    for t in df_bugun['ticker'][:40]:
        if t in cik_map:
            insider_bonus_map[t] = check_insider_buys(t, cik_map[t])
        option_data_map[t] = get_option_sentiment(t)
        time.sleep(0.1)

    df_final = calculate_us_scores(df_bugun, df_gecmis, df_yapisal, insider_bonus_map, option_data_map)
    df_final.to_csv("sonuclar.csv", index=False)
    
    # Geçmişe kaydet (Tüm sütunları koruyarak)
    df_kayit = df_final[['ticker', 'close', 'volume', 'change_%', 'quant_score', 'pc_ratio']].copy()
    df_kayit['tarih'] = bugun
    df_kayit.to_csv(GECMIS_DOSYA, mode='a', header=not os.path.exists(GECMIS_DOSYA), index=False)
    
    send_telegram_alert(df_final)

if __name__ == "__main__":
    run_daily()
