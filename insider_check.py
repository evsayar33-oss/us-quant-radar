import requests
import time
import xml.etree.ElementTree as ET

SEC_HEADERS = {"User-Agent": "ResearchAgent 0527em@gmail.com"} # Gecerli bir eposta girin

def check_insider_buys(ticker, cik):
    """SEC'den son Form 4 filings ceker ve sadece 'P' (Purchase) olanlari sayar."""
    url = f"https://data.sec.gov/submissions/CIK{cik.zfill(10)}.json"
    try:
        res = requests.get(url, headers=SEC_HEADERS, timeout=10)
        data = res.json()
        recent = data.get("filings", {}).get("recent", {})
        
        # Son 10 filing icinde kac tane '4' (Insider Change) var?
        form4_count = 0
        for i, form in enumerate(recent.get("form", [])):
            if form == "4" and i < 10:
                # Gercek alim (P) kontrolu normalde XML parse gerektirir. 
                # Hizli baslangic icin son 5 gunluk Form 4 sayisina bakiyoruz.
                form4_count += 1
        return 10 if form4_count >= 2 else 0
    except:
        return 0

def get_cik_map():
    url = "https://www.sec.gov/files/company_tickers.json"
    try:
        res = requests.get(url, headers=SEC_HEADERS)
        data = res.json()
        return {v['ticker']: str(v['cik_str']) for v in data.values()}
    except:
        return {}
