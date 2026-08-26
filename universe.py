import pandas as pd
import requests

def get_universe():
    """
    Tüm S&P 500, Nasdaq 100 ve yüksek momentumlu squeeze hisselerini 
    (Toplam 650+ hisse) dinamik olarak tek bir havuzda birleştirir.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    all_tickers = []
    
    # 1. Tam S&P 500 Listesi (503 Şirket)
    try:
        url_sp500 = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        df_sp = pd.read_html(url_sp500, storage_options=headers)[0]
        sp_tickers = df_sp['Symbol'].str.replace('.', '-', regex=False).tolist()
        all_tickers.extend(sp_tickers)
    except Exception as e:
        print(f"S&P 500 cekme hatasi: {e}")

    # 2. Tam Nasdaq 100 Listesi (100 Şirket)
    try:
        url_ndx = "https://en.wikipedia.org/wiki/Nasdaq-100"
        tables = pd.read_html(url_ndx, storage_options=headers)
        for t in tables:
            if 'Ticker' in t.columns:
                ndx_tickers = t['Ticker'].str.replace('.', '-', regex=False).tolist()
                all_tickers.extend(ndx_tickers)
                break
            elif 'Symbol' in t.columns:
                ndx_tickers = t['Symbol'].str.replace('.', '-', regex=False).tolist()
                all_tickers.extend(ndx_tickers)
                break
    except Exception as e:
        print(f"Nasdaq 100 cekme hatasi: {e}")

    # 3. Yüksek Beta, Kripto, AI ve Squeeze Hisseleri (Düşük Arz / Yüksek Volatilite)
    extra_momentum = [
        "ASTS", "RKLB", "LUNR", "SOUN", "BBAI", "IONQ", "RGTI", "QBTS", "QUBT",
        "LAES", "TEM", "PLTR", "AI", "PATH", "SMCI", "ARM", "SYM", "SERV", "SOUND",
        "GME", "AMC", "KOSS", "CVNA", "UPST", "AFRM", "OPEN", "CHWY", "BYND", "CAR",
        "SPCE", "SAVA", "NKLA", "BLNK", "CHPT", "CLOV", "WKHS",
        "MSTR", "MARA", "RIOT", "CLSK", "CIFR", "HUT", "BITF", "BTBT", "COIN",
        "HOOD", "CAN", "WULF", "IREN", "CORZ", "SOFI",
        "VKTX", "HIMS", "CRSP", "BEAM", "IBRX", "ARDX", "ALT", "TGTX", "KURA",
        "AXSM", "INSM", "MDGL", "RCKT", "MRNA", "BNTX", "NVAX", "OCGN",
        "JOBY", "ACHR", "EH", "RIVN", "LCID", "NIO", "XPEV", "QS", "PLUG",
        "FCEL", "ENVX", "SES", "SLDP", "STEM", "RUN", "ENPH", "SEDG",
        "RDDT", "DJT", "DKNG", "RBLX", "APP", "DUOL", "CELH", "CAVA", "ONON",
        "TOST", "BOWL", "ROOT", "W", "DASH", "CART"
    ]
    all_tickers.extend(extra_momentum)
    
    # Listeyi temizle, tekrar edenleri kaldır (Toplam ~650 hisse)
    cleaned = sorted(list(set([t.upper().strip() for t in all_tickers if isinstance(t, str) and len(t) <= 5])))
    return cleaned
