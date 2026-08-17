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
    if not token or not chat_id:
        print("Telegram ayarlari eksik, mesaj gonderilemedi.")
        return

    top_5 = df.head(5)
    msg = "🇺🇸 *US QUANT RADAR: TOP 5 SINYAL*\n"
    msg += "S&P500 & Nasdaq-100 Analizi\n\n"
    
    for _, r in top_5.iterrows():
        insider = "✅" if r['insider_bonus'] > 0 else "❌"
        msg += f"#{r['ticker']} | *Skor: {r['quant_score']:.1f}*\n"
        msg += f"• RVOL: {r['rvol_ratio']:.2f}x | Degisim: %{r['change_%']:.2f}\n"
        msg += f"• Yapisal Skor: {r['yapisal_skor']:.1f}\n"
        msg += f"• Insider Alim: {insider}\n\n"
    
    try:
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        requests.post(url, json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})
        print("Telegram mesaji gonderildi.")
    except Exception as e:
        print(f"Telegram hatasi: {e}")

def run_daily():
    est = pytz.timezone('US/Eastern')
    bugun = datetime.now(est).strftime('%Y-%m-%d')
    
    print(f"Tarama Basladi: {bugun}")
    
    # Not: [:100] kismini tum evreni taramak istersen silebilirsin
    tickers = get_universe()[:100] 
    df_bugun = gunluk_veri_cek(tickers)
    
    if df_bugun.empty:
        print("Veri cekilemedi, islem durduruldu.")
        return

    df_gecmis = pd.read_csv(GECMIS_DOSYA) if os.path.exists(GECMIS_DOSYA) else pd.DataFrame()
    df_yapisal = yapisal_gate_yukle()
    
    # Insider kontrolü (SEC limitleri icin sadece en iyi 20'ye bakalim)
    cik_map = get_cik_map()
    insider_bonus_map = {}
    for t in df_bugun['ticker'][:20]:
        if t in cik_map:
            insider_bonus_map[t] = check_insider_buys(t, cik_map[t])

    df_final = calculate_us_scores(df_bugun, df_gecmis, df_yapisal, insider_bonus_map)
    df_final.to_csv("sonuclar.csv", index=False)
    
    # Kayit
    df_bugun['tarih'] = bugun
    df_bugun.to_csv(GECMIS_DOSYA, mode='a', header=not os.path.exists(GECMIS_DOSYA), index=False)
    
    # Telegram Gonderimi
    send_telegram_alert(df_final)

if __name__ == "__main__":
    run_daily()
