import streamlit as st
import duckdb
import pandas as pd
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))

from scoring import compute_scores
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

def show_report(ticker, df):
    company_df = df[df["ticker"] == ticker].sort_values("year")

    if company_df.empty:
        st.error(f"No data found for {ticker}. Try AAPL, MSFT, AMZN, NVDA, or TSLA.")
        return

    latest = company_df.iloc[-1]

    # Header
    st.markdown(f"## Financial Health Report — {ticker}")
    st.markdown(f"**Latest data year: {int(latest['year'])}**")
    st.divider()

    # Overall score
    score = latest["overall_score"]
    if score >= 8:
        color = "🟢"
    elif score >= 6:
        color = "🟡"
    else:
        color = "🔴"

    st.markdown(f"### {color} Overall Health Score: {score} / 10")
    st.markdown(translate_overall(latest))
    st.divider()

    # Pillar scores as a bar chart
    st.markdown("### Pillar Breakdown")
    pillar_data = pd.DataFrame({
        "Pillar": ["Profitability", "Cash Flow", "Debt Safety", "Growth"],
        "Score": [
            latest["profitability_score"],
            latest["cashflow_score"],
            latest["debt_score"],
            latest["growth_score"]
        ]
    })
    st.bar_chart(pillar_data.set_index("Pillar"))
    st.divider()

    # Pillar details
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

    # Trend story
    st.markdown("### Trend Story")
    first = company_df.iloc[0]
    if pd.notna(first["revenue"]) and pd.notna(latest["revenue"]):
        rev_change = round(((latest["revenue"] - first["revenue"]) / first["revenue"]) * 100, 1)
        direction = "grown" if rev_change > 0 else "declined"
        st.markdown(f"Over the past {len(company_df)} years, **{ticker}'s revenue has {direction} by {abs(rev_change)}%**.")
    if pd.notna(first["profit_margin"]) and pd.notna(latest["profit_margin"]):
        margin_change = round((latest["profit_margin"] - first["profit_margin"]) * 100, 1)
        direction = "improved" if margin_change > 0 else "declined"
        st.markdown(f"Profit margins have **{direction} by {abs(margin_change)} percentage points** over this period.")

    # Score over time chart
    st.markdown("### Overall Score Over Time")
    st.line_chart(company_df.set_index("year")["overall_score"])


# --- Main App ---
st.set_page_config(page_title="Financial Health Analyzer", layout="centered")
st.title("📊 Financial Health Analyzer")
st.markdown("Get a plain-English financial health report for any major public company.")

ticker_input = st.text_input("Enter a ticker symbol", placeholder="e.g. AAPL, MSFT, AMZN, NVDA, TSLA").upper().strip()

if ticker_input:
    with st.spinner(f"Generating report for {ticker_input}..."):
        df = load_data()
        show_report(ticker_input, df)