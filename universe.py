import pandas as pd

def get_universe():
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        # S&P 500
        sp500 = pd.read_html("https://en.wikipedia.org/wiki/List_of_S%26P_500_companies", storage_options=headers)[0]
        sp500_tickers = sp500['Symbol'].str.replace('.', '-', regex=False).tolist()
        
        # Nasdaq 100
        nasdaq100 = pd.read_html("https://en.wikipedia.org/wiki/Nasdaq-100", storage_options=headers)
        nasdaq_tickers = []
        for tbl in nasdaq100:
            if 'Ticker' in tbl.columns:
                nasdaq_tickers = tbl['Ticker'].tolist()
                break
        
        evren = sorted(set(sp500_tickers) | set(nasdaq_tickers))
        return evren
    except Exception as e:
        print(f"Evren olusturma hatasi: {e}")
        return []
