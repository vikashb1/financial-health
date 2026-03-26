import requests
import pandas as pd
import re
import json
import os
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from sklearn.feature_extraction.text import TfidfVectorizer
from textblob import TextBlob

HEADERS = {"User-Agent": "vikashraghavenderbabu@gmail.com"}

TICKERS = {
    # Tech
    "AAPL": "0000320193",
    "MSFT": "0000789019",
    "AMZN": "0001018724",
    "NVDA": "0001045810",
    "TSLA": "0001318605",
    "GOOGL": "0001652044",
    "META": "0001326801",
    "NFLX": "0001065280",
    "AMD": "0000002488",
    "INTC": "0000050863",
    # Healthcare
    "JNJ": "0000200406",
    "PFE": "0000078003",
    "UNH": "0000731766",
    "ABBV": "0001551152",
    "MRK": "0000310158",
    # Finance
    "JPM": "0000019617",
    "BAC": "0000070858",
    "WFC": "0000072971",
    "GS": "0000886982",
    "MS": "0000895421",
    # Retail
    "WMT": "0000104169",
    "TGT": "0000027419",
    "COST": "0000909832",
    "HD": "0000354950",
    "NKE": "0000320187",
    # Energy
    "XOM": "0000034088",
    "CVX": "0000093410",
    "COP": "0001163165",
    # Industrial
    "BA": "0000012927",
    "CAT": "0000018230",
}

def get_10k_filings(cik, count=5):
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(url, headers=HEADERS).json()
    filings = r["filings"]["recent"]
    df = pd.DataFrame({
        "form": filings["form"],
        "date": filings["filingDate"],
        "accession": filings["accessionNumber"]
    })
    df = df[df["form"] == "10-K"].head(count)
    return df

def get_risk_text(cik, accession):
    accession_clean = accession.replace("-", "")
    try:
        index_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/index.json"
        r = requests.get(index_url, headers=HEADERS, timeout=10)
        index = r.json()
        items = index.get("directory", {}).get("item", [])

        main_doc = None
        for item in items:
            name = item["name"]
            if (name.endswith(".htm") and
                not name.startswith("R") and
                not name.startswith("a10-k") and
                "index" not in name.lower()):
                main_doc = name
                break

        if not main_doc:
            return ""

        doc_url = f"https://www.sec.gov/Archives/edgar/data/{int(cik)}/{accession_clean}/{main_doc}"
        doc_r = requests.get(doc_url, headers=HEADERS, timeout=30)
        text = doc_r.text

        text = re.sub(r'<[^>]+>', ' ', text)
        text = text.replace('&#160;', ' ').replace('&nbsp;', ' ')
        text = text.replace('&#8220;', '"').replace('&#8221;', '"')
        text = re.sub(r'\s+', ' ', text)

        matches = list(re.finditer(r'1A[\.\s]+Risk\s+Factors', text, re.IGNORECASE))
        end_match = re.search(r'1B[\.\s]+Unresolved\s+Staff\s+Comments', text, re.IGNORECASE)

        if matches:
            start = matches[-1]
            if end_match and end_match.start() > start.start():
                return text[start.start():end_match.start()]
            else:
                return text[start.start():start.start() + 15000]

    except Exception as e:
        pass
    return ""

def clean_text(text):
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text)
    text = text.lower()
    stop_words = set(stopwords.words('english'))
    custom_stops = {
        'item', 'factors', 'factor', 'form', 'report', 'annual',
        'risk', 'risks', 'company', 'also', 'may', 'could', 'would',
        'including', 'result', 'results', 'affect', 'significant',
        'ability', 'future', 'impact', 'change', 'changes', 'related',
        'subject', 'following', 'number', 'period', 'year', 'years',
        'quarter', 'business', 'products', 'services', 'operations',
        'financial', 'based', 'stock', 'market', 'operate', 'operating'
    }
    stop_words.update(custom_stops)
    tokens = word_tokenize(text)
    tokens = [t for t in tokens if t.isalpha() and t not in stop_words and len(t) > 4]
    return ' '.join(tokens)

def get_top_risk_themes(texts, n=10):
    if not texts:
        return []
    vectorizer = TfidfVectorizer(max_features=100, ngram_range=(1, 2))
    try:
        tfidf = vectorizer.fit_transform(texts)
        scores = tfidf.toarray().mean(axis=0)
        terms = vectorizer.get_feature_names_out()
        top = sorted(zip(terms, scores), key=lambda x: x[1], reverse=True)[:n]
        return [term for term, score in top]
    except:
        return []

def get_sentiment(text):
    blob = TextBlob(text[:3000])
    return round(blob.sentiment.polarity, 3)

def categorize_risk(theme):
    theme_lower = theme.lower()
    if any(w in theme_lower for w in ['regulat', 'legal', 'compliance', 'government', 'legislation']):
        return 'Regulatory'
    elif any(w in theme_lower for w in ['compet', 'market share', 'rival', 'competition']):
        return 'Competition'
    elif any(w in theme_lower for w in ['supply', 'manufactur', 'component', 'vendor', 'supplier']):
        return 'Supply Chain'
    elif any(w in theme_lower for w in ['cyber', 'secur', 'data', 'privacy', 'breach']):
        return 'Cybersecurity'
    elif any(w in theme_lower for w in ['macroeconom', 'recession', 'inflation', 'interest', 'economic']):
        return 'Macroeconomic'
    elif any(w in theme_lower for w in ['technology', 'innovat', 'cloud', 'artificial', 'intelligence']):
        return 'Technology'
    else:
        return 'General'

def analyze_company(ticker, cik):
    print(f"Analyzing {ticker}...")
    filings = get_10k_filings(cik)

    all_texts = []
    results = []

    for _, row in filings.iterrows():
        text = get_risk_text(str(int(cik)), row["accession"])
        if text:
            cleaned = clean_text(text)
            sentiment = get_sentiment(text)
            all_texts.append(cleaned)
            results.append({
                "ticker": ticker,
                "date": row["date"],
                "sentiment": sentiment,
                "raw_length": len(text)
            })

    if not all_texts:
        print(f"  No risk text found for {ticker}")
        return None

    themes = get_top_risk_themes(all_texts)
    top_3 = themes[:3]
    categorized = [(t, categorize_risk(t)) for t in top_3]

    print(f"  Top risks: {top_3}")
    print(f"  Avg sentiment: {round(sum(r['sentiment'] for r in results) / len(results), 3)}")

    return {
        "ticker": ticker,
        "top_risks": categorized,
        "avg_sentiment": round(sum(r["sentiment"] for r in results) / len(results), 3),
        "sentiment_trend": "Worsening" if results[-1]["sentiment"] < results[0]["sentiment"] else "Stable or Improving"
    }

def run_nlp_pipeline():
    os.makedirs("data/mart", exist_ok=True)
    all_results = {}

    for ticker, cik in TICKERS.items():
        result = analyze_company(ticker, cik)
        if result:
            all_results[ticker] = result

    with open("data/mart/risk_analysis.json", "w") as f:
        json.dump(all_results, f, indent=2)

    print("\nDone. Risk analysis saved to data/mart/risk_analysis.json")
    return all_results

if __name__ == "__main__":
    run_nlp_pipeline()