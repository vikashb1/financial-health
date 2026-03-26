content = '''import streamlit as st
import duckdb
import pandas as pd
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

st.set_page_config(page_title="Financial Health Analyzer", layout="centered")

from translation import (
    translate_profitability,
    translate_cashflow,
    translate_debt,
    translate_growth,
    translate_overall
)

def load_data():
    con_mart = duckdb.connect("data/mart/mart.duckdb")
    scores = con_mart.execute("SELECT * FROM scored_company_year ORDER BY ticker, year").df()
    con_mart.close()
    con_staged = duckdb.connect("data/staged/financials.duckdb")
    staged = con_staged.execute("SELECT ticker, year, revenue FROM staged_financials").df()
    con_staged.close()
    df = scores.merge(staged, on=["ticker", "year"], how="left")
    return df

def load_risk_data():
    try:
        with open("data/mart/risk_analysis.json", "r") as f:
            return json.load(f)
    except:
        return {}

def load_evaluation():
    try:
        df = pd.read_csv("reports/evaluation.csv")
        with open("reports/evaluation_summary.json", "r") as f:
            summary = json.load(f)
        return df, summary
    except:
        return None, None

def show_report(ticker, df):
    company_df = df[df["ticker"] == ticker].sort_values("year")
    if company_df.empty:
        st.error(f"No data found for {ticker}. Try AAPL, MSFT, AMZN, NVDA, or TSLA.")
        return
    latest = company_df.iloc[-1]
    st.markdown(f"## Financial Health Report - {ticker}")
    st.markdown(f"**Latest data year: {int(latest['year'])}**")
    st.divider()
    score = latest["overall_score"]
    color = "green" if score >= 8 else "orange" if score >= 6 else "red"
    st.markdown(f"### Overall Health Score: {score} / 10")
    st.markdown(translate_overall(latest))
    st.divider()
    st.markdown("### Pillar Breakdown")
    pillar_data = pd.DataFrame({
        "Pillar": ["Profitability", "Cash Flow", "Debt Safety", "Growth"],
        "Score": [latest["profitability_score"], latest["cashflow_score"], latest["debt_score"], latest["growth_score"]]
    })
    st.bar_chart(pillar_data.set_index("Pillar"))
    st.divider()
    st.markdown("### Profitability")
    st.markdown(f"**Score: {latest['profitability_score']} / 10**")
    st.markdown(translate_profitability(latest))
    st.markdown("### Cash Flow")
    st.markdown(f"**Score: {latest['cashflow_score']} / 10**")
    st.markdown(translate_cashflow(latest))
    st.markdown("### Debt Safety")
    st.markdown(f"**Score: {latest['debt_score']} / 10**")
    st.markdown(translate_debt(latest))
    st.markdown("### Growth")
    st.markdown(f"**Score: {latest['growth_score']} / 10**")
    st.markdown(translate_growth(latest))
    st.divider()
    st.markdown("### Top Risk Themes")
    risk_data = load_risk_data()
    if ticker in risk_data:
        rd = risk_data[ticker]
        st.markdown(f"**Sentiment Trend:** {rd['sentiment_trend']}")
        for theme, category in rd["top_risks"]:
            st.markdown(f"- **{category}:** {theme}")
    else:
        st.markdown("Risk analysis not available for this company.")
    st.divider()
    st.markdown("### Trend Story")
    first = company_df.iloc[0]
    if pd.notna(first["revenue"]) and pd.notna(latest["revenue"]):
        rev_change = round(((latest["revenue"] - first["revenue"]) / first["revenue"]) * 100, 1)
        direction = "grown" if rev_change > 0 else "declined"
        st.markdown(f"Over the past {len(company_df)} years, **{ticker} revenue has {direction} by {abs(rev_change)}%**.")
    if pd.notna(first["profit_margin"]) and pd.notna(latest["profit_margin"]):
        margin_change = round((latest["profit_margin"] - first["profit_margin"]) * 100, 1)
        direction = "improved" if margin_change > 0 else "declined"
        st.markdown(f"Profit margins have **{direction} by {abs(margin_change)} percentage points** over this period.")
    st.markdown("### Overall Score Over Time")
    st.line_chart(company_df.set_index("year")["overall_score"])

def show_evaluation():
    st.markdown("## Model Validation")
    st.markdown("Does the health score actually mean something? We tested it against real stock volatility.")
    st.divider()
    eval_df, summary = load_evaluation()
    if eval_df is None:
        st.warning("Evaluation data not found. Run src/evaluation.py first.")
        return
    correlation = summary["correlation"]
    st.markdown(f"### Correlation: {correlation}")
    st.markdown("A negative correlation means companies with higher health scores tend to have lower stock volatility.")
    st.markdown("### Score vs Volatility by Company")
    company_avg = eval_df.groupby("ticker")[["overall_score", "volatility"]].mean().round(3)
    st.dataframe(company_avg)
    st.markdown("### Volatility Over Time by Company")
    pivot = eval_df.pivot(index="year", columns="ticker", values="volatility")
    st.line_chart(pivot)
    st.markdown("### Health Score Over Time by Company")
    pivot_score = eval_df.pivot(index="year", columns="ticker", values="overall_score")
    st.line_chart(pivot_score)

st.title("Financial Health Analyzer")
st.markdown("Get a plain-English financial health report for any major public company.")
page = st.radio("Select view", ["Company Report", "Model Validation"], horizontal=True)
if page == "Company Report":
    ticker_input = st.text_input("Enter a ticker symbol", placeholder="e.g. AAPL, MSFT, AMZN, NVDA, TSLA").upper().strip()
    if ticker_input:
        with st.spinner(f"Generating report for {ticker_input}..."):
            df = load_data()
            show_report(ticker_input, df)
elif page == "Model Validation":
    show_evaluation()
'''

with open("app.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Done - app.py written successfully")
print("Lines:", len(content.splitlines()))