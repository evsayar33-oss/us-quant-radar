import os, pandas as pd, requests, time, pytz
from datetime import datetime
from universe import get_universe
from structural_gate import yapisal_gate_yukle
from insider_check import get_cik_map, check_insider_buys
from quant_engine_us import gunluk_veri_cek, calculate_us_scores, get_advanced_option_metrics, GECMIS_DOSYA

def send_telegram_alert(df):
    token, chat_id = os.environ.get("TELEGRAM_TOKEN"), os.environ.get("CHAT_ID")
    if not token or not chat_id: return
    
    top_10 = df.head(10)
    msg = "🛡️ *US INSTITUTIONAL SENTINEL (V3)*\n"
    msg += "Hisse | Skor | OI Mom | Skew\n"
    msg += "------------------------------\n"
    for _, r in top_10.iterrows():
        msg += f"• #{r['ticker']}: *{r['quant_score']:.1f}* | %{r['pct_oi_mom']:.0f} | %{r['pct_skew']:.0f}\n"
    
    requests.post(f"https://api.telegram.org/bot{token}/sendMessage", json={"chat_id": chat_id, "text": msg, "parse_mode": "Markdown"})

def run_daily():
    est = pytz.timezone('US/Eastern')
    bugun = datetime.now(est).strftime('%Y-%m-%d')
    
    tickers = get_universe()[:250] # S&P + Nasdaq Top 250
    df_bugun = gunluk_veri_cek(tickers)
    if df_bugun.empty: return

    df_gecmis = pd.read_csv(GECMIS_DOSYA) if os.path.exists(GECMIS_DOSYA) else pd.DataFrame()
    df_yapisal = yapisal_gate_yukle()
    cik_map = get_cik_map()
    
    # 40 ADAY İÇİN DERİN TÜREV ANALİZİ
    insider_map, opt_map = {}, {}
    for t in df_bugun['ticker'][:40]:
        if t in cik_map:
            insider_map[t] = check_insider_buys(t, cik_map[t])
        opt_map[t] = get_advanced_option_metrics(t)
        time.sleep(0.2) # SEC/Yahoo nezaket beklemesi

    df_final = calculate_us_scores(df_bugun, df_gecmis, df_yapisal, insider_map, opt_map)
    df_final.to_csv("sonuclar.csv", index=False)
    
    # Hafızaya ekle (Yeni sütunlar dahil)
    df_kayit = df_final[['ticker', 'close', 'volume', 'quant_score', 'option_oi']].copy()
    df_kayit['tarih'] = bugun
    df_kayit.to_csv(GECMIS_DOSYA, mode='a', header=not os.path.exists(GECMIS_DOSYA), index=False)
    
    send_telegram_alert(df_final)

if __name__ == "__main__":
    run_daily()
