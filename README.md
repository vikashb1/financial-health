# Financial Health Analyzer

An end-to-end data analytics platform that ingests real financial data from SEC EDGAR filings, scores company financial health across four pillars, and generates plain-English reports — accessible through a web interface.

---

## What It Does

Most people can't read a 10-K filing. This tool pulls the data from those filings and translates it into a clear, human-readable financial health report — no accounting knowledge required.

You type a ticker. You get a report.

---

## Features

- **Automated data pipeline** — pulls structured financial data from the SEC EDGAR XBRL API for 5 major companies across 7 years
- **Feature engineering** — computes profit margins, cash flow ratios, debt-to-assets, revenue growth, and margin trends
- **4-pillar scoring model** — scores Profitability, Cash Flow, Debt Safety, and Growth on a 0–10 scale with configurable weights
- **Plain-English translation** — rule-based engine converts numerical signals into readable narrative
- **NLP risk analysis** — extracts and categorizes risk themes from real 10-K filings using TF-IDF and sentiment analysis
- **Model validation** — correlates health scores with stock volatility (r = -0.37), confirming the model captures real financial signal
- **Web interface** — Streamlit app with company reports and model validation page

---

## Tech Stack

| Layer | Tools |
|---|---|
| Data Ingestion | Python, SEC EDGAR API, requests |
| Storage | DuckDB (3-layer: raw → staged → mart) |
| Feature Engineering | pandas, numpy |
| NLP | NLTK, scikit-learn (TF-IDF), TextBlob |
| Scoring | Rule-based weighted model |
| Validation | yfinance, pandas |
| Web App | Streamlit |

---

## Project Structure
```
financial-health/
├── src/
│   ├── ingestion.py       # SEC EDGAR data pipeline
│   ├── features.py        # Feature engineering
│   ├── scoring.py         # 4-pillar scoring model
│   ├── translation.py     # Plain-English report generation
│   ├── nlp.py             # Risk factor text mining
│   └── evaluation.py      # Model validation
├── data/
│   ├── staged/            # Cleaned financial data (DuckDB)
│   └── mart/              # Engineered features + scores (DuckDB)
├── reports/               # Evaluation results
├── app.py                 # Streamlit web application
└── README.md
```

---

## How To Run

**1. Install dependencies**
```bash
pip install requests pandas duckdb streamlit nltk scikit-learn textblob yfinance
python -c "import nltk; nltk.download('stopwords'); nltk.download('punkt_tab'); nltk.download('vader_lexicon')"
```

**2. Run the pipeline**
```bash
python src/ingestion.py      # Pull data from SEC EDGAR
python src/features.py       # Engineer features
python src/scoring.py        # Compute health scores
python src/translation.py    # Generate text reports
python src/nlp.py            # Run NLP on risk factors
python src/evaluation.py     # Validate against stock volatility
```

**3. Launch the web app**
```bash
streamlit run app.py
```

---

## Sample Output — AAPL (2025)

| Pillar | Score | Signal |
|---|---|---|
| Profitability | 10 / 10 | 26.9% profit margin |
| Cash Flow | 10 / 10 | 26.8% OCF margin |
| Debt Safety | 7 / 10 | 25.2% debt-to-assets |
| Growth | 6 / 10 | +6.4% revenue growth |
| **Overall** | **8.65 / 10** | Financially strong |

> "AAPL is financially strong in 2025 with no major concerns. Over 7 years, revenue has grown by 60.0% and profit margins have improved by 5.7 percentage points."

---

## Validation

Correlation between health score and stock volatility: **-0.37**

Healthier companies (MSFT, AAPL) show lower volatility. Riskier companies (TSLA, NVDA) show higher volatility. This confirms the scoring model captures real financial signal.

| Company | Avg Health Score | Avg Volatility |
|---|---|---|
| MSFT | 9.13 | 0.271 |
| AAPL | 8.19 | 0.298 |
| AMZN | 6.77 | 0.331 |
| NVDA | 7.37 | 0.492 |
| TSLA | 7.01 | 0.627 |

---

## Skills Demonstrated

**Data Engineering** — REST API ingestion, multi-layer data warehouse, idempotent pipeline, data quality validation

**Data Analysis** — financial ratio computation, trend analysis, interpretable scoring, business narrative generation

**Data Science / NLP** — TF-IDF vectorization, risk theme extraction, sentiment analysis, model evaluation