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

    # 1. Liderler (Top 10)
    top_10 = df.head(10)
    # 2. Güç Kaybedenler (Skor Farkı En Çok Düşen 10)
    losers_10 = df.sort_values(by='score_diff', ascending=True).head(10)

    msg = "🏆 *US QUANT LİDERLER (TOP 10)*\n"
    msg += "Hisse | Skor | (Fark)\n"
    msg += "---------------------------\n"
    for _, r in top_10.iterrows():
        mood = "🔥" if r['pct_pc_rank'] > 80 else "N"
        msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* ({r['score_diff']:+.1f}) {mood}\n"

    msg += "\n📉 *SKORU EN ÇOK DÜŞENLER (TOP 10)*\n"
    msg += "Hisse | Skor | (Fark)\n"
    msg += "---------------------------\n"
    for _, r in losers_10.iterrows():
        # Sadece gerçekten düşüş olanları ünlemle işaretle
        if r['score_diff'] < 0:
            msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* ⚠️ {r['score_diff']:.1f}\n"
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
        print("Telegram mesaji gonderildi.")
    except Exception as e:
        print(f"Telegram hatasi: {e}")

def run_daily():
    est = pytz.timezone('US/Eastern')
    bugun = datetime.now(est).strftime('%Y-%m-%d')
    
    # 250 hisselik evren
    tickers = get_universe()[:250] 
    df_bugun = gunluk_veri_cek(tickers)
    if df_bugun.empty: return

    df_gecmis = pd.read_csv(GECMIS_DOSYA) if os.path.exists(GECMIS_DOSYA) else pd.DataFrame()
    df_yapisal = yapisal_gate_yukle()
    cik_map = get_cik_map()
    
    insider_bonus_map = {}
    option_data_map = {}
    
    # En iyi 40 adayı analiz et (Hız ve Limit koruması)
    for t in df_bugun['ticker'][:40]:
        if t in cik_map:
            insider_bonus_map[t] = check_insider_buys(t, cik_map[t])
        option_data_map[t] = get_option_sentiment(t)
        time.sleep(0.1)

    df_final = calculate_us_scores(df_bugun, df_gecmis, df_yapisal, insider_bonus_map, option_data_map)
    df_final.to_csv("sonuclar.csv", index=False)
    
    # Kayıt (Hafıza için)
    df_kayit = df_final[['ticker', 'close', 'volume', 'change_%', 'quant_score', 'pc_ratio']].copy()
    df_kayit['tarih'] = bugun
    df_kayit.to_csv(GECMIS_DOSYA, mode='a', header=not os.path.exists(GECMIS_DOSYA), index=False)
    
    send_telegram_alert(df_final)

if __name__ == "__main__":
    run_daily()
