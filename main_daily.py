import os
import pandas as pd
import requests
from datetime import datetime
import pytz
from universe import get_universe
from structural_gate import yapisal_gate_yukle
from insider_check import get_cik_map, check_insider_buys
from quant_engine_us import gunluk_veri_cek, calculate_us_scores, GECMIS_DOSYA

def send_telegram_alert(df):
    token = os.environ.get("TELEGRAM_TOKEN")
    chat_id = os.environ.get("CHAT_ID")
    if not token or not chat_id: return

    top_10 = df.head(10)
    losers_10 = df.sort_values(by='score_diff', ascending=True).head(10)

    msg = "🇺🇸 *US QUANT LİDERLER (TOP 10)*\n"
    for _, r in top_10.iterrows():
        msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* ({r['score_diff']:+.1f})\n"

    msg += "\n📉 *GÜÇ KAYBEDENLER (ÇIKIŞ SİNYALİ)*\n"
    for _, r in losers_10.iterrows():
        if r['score_diff'] < -1:
            msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* ⚠️ {r['score_diff']:.1f}\n"
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
    except:
        print("Telegram hatasi.")

def run_daily():
    est = pytz.timezone('US/Eastern')
    bugun = datetime.now(est).strftime('%Y-%m-%d')
    
    # Wikipedia'dan evreni çek ve ilk 250 hisseye bak
    tickers = get_universe()[:250] 
    df_bugun = gunluk_veri_cek(tickers)
    
    if df_bugun.empty:
        print("Veri cekilemedi.")
        return

    df_gecmis = pd.read_csv(GECMIS_DOSYA) if os.path.exists(GECMIS_DOSYA) else pd.DataFrame()
    df_yapisal = yapisal_gate_yukle()
    cik_map = get_cik_map()
    
    # Insider bonusları
    insider_bonus_map = {}
    for t in df_bugun['ticker'][:30]: # En yüksek hacimli 30 hisse için
        if t in cik_map:
            insider_bonus_map[t] = check_insider_buys(t, cik_map[t])

    df_final = calculate_us_scores(df_bugun, df_gecmis, df_yapisal, insider_bonus_map)
    df_final.to_csv("sonuclar.csv", index=False)
    
    # Geçmişe kaydet (Tarihsel analiz için)
    df_kayit = df_final[['ticker', 'close', 'volume', 'change_%', 'quant_score']].copy()
    df_kayit['tarih'] = bugun
    df_kayit.to_csv(GECMIS_DOSYA, mode='a', header=not os.path.exists(GECMIS_DOSYA), index=False)
    
    send_telegram_alert(df_final)

if __name__ == "__main__":
    run_daily()
