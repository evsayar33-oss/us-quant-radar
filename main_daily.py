import os
import pandas as pd
import requests
import time
from datetime import datetime
import pytz
from universe import get_universe
from structural_gate import yapisal_gate_yukle
from insider_check import get_cik_map, check_insider_buys
from quant_engine_us import gunluk_veri_cek, calculate_us_scores, get_advanced_option_metrics, GECMIS_DOSYA

def send_telegram_alert(df):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id: return

    # Liderler ve Dusenler
    top_10 = df.head(10)
    losers_10 = df.sort_values(by='score_diff', ascending=True).head(10)

    msg = "🛡️ *US INSTITUTIONAL SENTINEL (V3)*\n"
    msg += "Hisse | Skor | OI Mom | Skew\n"
    msg += "------------------------------\n"
    for _, r in top_10.iterrows():
        msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* | %{r['pct_oi_mom']:.0f} | %{r['pct_skew']:.0f}\n"

    msg += "\n📉 *EN COK DUSENLER*\n"
    for _, r in losers_10.iterrows():
        if r['score_diff'] < 0:
            msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* ⚠️ {r['score_diff']:.1f}\n"
    
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", 
                  json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

def run_daily():
    est = pytz.timezone('US/Eastern')
    bugun = datetime.now(est).strftime('%Y-%m-%d')
    
    tickers = get_universe()[:250] 
    df_bugun = gunluk_veri_cek(tickers)
    if df_bugun.empty:
        print("Hata: Fiyat verileri cekilemedi.")
        return

    df_gecmis = pd.read_csv(GECMIS_DOSYA) if os.path.exists(GECMIS_DOSYA) else pd.DataFrame()
    df_yapisal = yapisal_gate_yukle()
    cik_map = get_cik_map()
    
    insider_map, opt_map = {}, {}
    for t in df_bugun['ticker'][:40]:
        if t in cik_map:
            insider_map[t] = check_insider_buys(t, cik_map[t])
        opt_map[t] = get_advanced_option_metrics(t)
        time.sleep(0.1)

    df_final = calculate_us_scores(df_bugun, df_gecmis, df_yapisal, insider_map, opt_map)
    df_final.to_csv("sonuclar.csv", index=False)
    
    # Gecmise kaydet
    df_kayit = df_final[['ticker', 'close', 'volume', 'quant_score', 'option_oi']].copy()
    df_kayit['tarih'] = bugun
    df_kayit.to_csv(GECMIS_DOSYA, mode='a', header=not os.path.exists(GECMIS_DOSYA), index=False)
    
    send_telegram_alert(df_final)

if __name__ == "__main__":
    run_daily()
