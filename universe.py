import pandas as pd
import requests

def get_universe():
    """Hacmi yuksek ve islem goren genis hisse evrenini ceker."""
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # S&P 500 listesi baz olarak baslar
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        df = pd.read_html(url, storage_options=headers)[0]
        tickers = df['Symbol'].str.replace('.', '-', regex=False).tolist()
        
        # Ekstra: Russell 2000'den onemli momentum hisseleri veya populer tickerlar
        # Sistemi yormamak icin ilk 350 hisseye odaklanacagiz
        return tickers[:350]
    except:
        return ["AAPL", "TSLA", "NVDA", "AMD", "META", "AMZN", "MSFT", "GOOGL", "GME", "AMC"]
