import streamlit as st
import duckdb
import pandas as pd
import json
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
st.set_page_config(page_title="Financial Health Analyzer", layout="wide")

from translation import translate_profitability, translate_cashflow, translate_debt, translate_growth, translate_overall

def load_data():
    con_mart = duckdb.connect("data/mart/mart.duckdb")
    scores = con_mart.execute("SELECT * FROM scored_company_year ORDER BY ticker, year").df()
    con_mart.close()
    con_staged = duckdb.connect("data/staged/financials.duckdb")
    staged = con_staged.execute("SELECT ticker, year, revenue FROM staged_financials").df()
    con_staged.close()
    return scores.merge(staged, on=["ticker", "year"], how="left")

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
            return df, json.load(f)
    except:
        return None, None

def load_sectors():
    try:
        with open("data/mart/sectors.json", "r") as f:
            return json.load(f)
    except:
        return {}

def load_predictions():
    try:
        return pd.read_csv("reports/predictions.csv")
    except:
        return None

def load_ml_metrics():
    try:
        with open("reports/ml_metrics.json", "r") as f:
            return json.load(f)
    except:
        return None

def show_company_card(ticker, df, col):
    company_df = df[df["ticker"] == ticker].sort_values("year")
    if company_df.empty:
        col.error(f"No data found for {ticker}.")
        return
    latest = company_df.iloc[-1]
    score = latest["overall_score"]
    color = "🟢" if score >= 8 else "🟡" if score >= 6 else "🔴"
    col.markdown(f"## {ticker}")
    col.markdown(f"{color} **Overall Score: {score} / 10**")
    col.markdown(translate_overall(latest))
    col.divider()
    col.markdown("### Pillar Scores")
    pillar_data = pd.DataFrame({
        "Pillar": ["Profitability", "Cash Flow", "Debt Safety", "Growth"],
        "Score": [latest["profitability_score"], latest["cashflow_score"], latest["debt_score"], latest["growth_score"]]
    })
    col.bar_chart(pillar_data.set_index("Pillar"))
    col.divider()
    col.markdown(f"**Profitability ({latest['profitability_score']}/10):** {translate_profitability(latest)}")
    col.markdown(f"**Cash Flow ({latest['cashflow_score']}/10):** {translate_cashflow(latest)}")
    col.markdown(f"**Debt Safety ({latest['debt_score']}/10):** {translate_debt(latest)}")
    col.markdown(f"**Growth ({latest['growth_score']}/10):** {translate_growth(latest)}")
    col.divider()
    col.markdown("### Score Over Time")
    col.line_chart(company_df.set_index("year")["overall_score"])

def show_report(ticker, df):
    company_df = df[df["ticker"] == ticker].sort_values("year")
    if company_df.empty:
        st.error(f"No data found for {ticker}.")
        return
    latest = company_df.iloc[-1]
    st.markdown(f"## Financial Health Report - {ticker}")
    st.markdown(f"**Latest data year: {int(latest['year'])}**")
    st.divider()
    score = latest["overall_score"]
    color = "🟢" if score >= 8 else "🟡" if score >= 6 else "🔴"
    st.markdown(f"### {color} Overall Health Score: {score} / 10")
    st.markdown(translate_overall(latest))
    predictions = load_predictions()
    if predictions is not None:
        row = predictions[predictions["ticker"] == ticker]
        if not row.empty:
            pred = row.iloc[0]["predicted_next_score"]
            trend = row.iloc[0]["trend"]
            arrow = "↑" if trend == "Up" else "↓" if trend == "Down" else "→"
            st.markdown(f"**ML Prediction for next year:** {pred} / 10 {arrow}")
    st.divider()
    st.markdown("### Pillar Breakdown")
    pillar_data = pd.DataFrame({"Pillar": ["Profitability", "Cash Flow", "Debt Safety", "Growth"], "Score": [latest["profitability_score"], latest["cashflow_score"], latest["debt_score"], latest["growth_score"]]})
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
        st.markdown("Risk analysis not available.")
    st.divider()
    st.markdown("### Trend Story")
    first = company_df.iloc[0]
    if pd.notna(first["revenue"]) and pd.notna(latest["revenue"]):
        rev_change = round(((latest["revenue"] - first["revenue"]) / first["revenue"]) * 100, 1)
        st.markdown(f"Over {len(company_df)} years, **{ticker} revenue has {'grown' if rev_change > 0 else 'declined'} by {abs(rev_change)}%**.")
    if pd.notna(first["profit_margin"]) and pd.notna(latest["profit_margin"]):
        margin_change = round((latest["profit_margin"] - first["profit_margin"]) * 100, 1)
        st.markdown(f"Profit margins have **{'improved' if margin_change > 0 else 'declined'} by {abs(margin_change)} percentage points**.")
    st.markdown("### Overall Score Over Time")
    st.line_chart(company_df.set_index("year")["overall_score"])

def show_compare(df):
    st.markdown("## Company Comparison")
    st.markdown("Compare two companies side by side.")
    st.divider()
    col1, col2 = st.columns(2)
    ticker1 = col1.text_input("First company", placeholder="e.g. AAPL").upper().strip()
    ticker2 = col2.text_input("Second company", placeholder="e.g. MSFT").upper().strip()
    if ticker1 and ticker2:
        st.divider()
        c1, c2 = st.columns(2)
        show_company_card(ticker1, df, c1)
        show_company_card(ticker2, df, c2)
        st.divider()
        st.markdown("### Head to Head — Score Over Time")
        t1_df = df[df["ticker"] == ticker1].sort_values("year").set_index("year")["overall_score"]
        t2_df = df[df["ticker"] == ticker2].sort_values("year").set_index("year")["overall_score"]
        combined = pd.DataFrame({ticker1: t1_df, ticker2: t2_df})
        st.line_chart(combined)

def show_evaluation():
    st.markdown("## Model Validation")
    st.markdown("Does the health score actually mean something? We tested it against real stock volatility.")
    st.divider()
    eval_df, summary = load_evaluation()
    if eval_df is None:
        st.warning("Run src/evaluation.py first.")
        return
    st.markdown(f"### Correlation: {summary['correlation']}")
    st.markdown("Negative correlation means healthier companies have lower stock volatility.")
    st.markdown("### Score vs Volatility by Company")
    st.dataframe(eval_df.groupby("ticker")[["overall_score", "volatility"]].mean().round(3))
    st.markdown("### Volatility Over Time")
    st.line_chart(eval_df.pivot(index="year", columns="ticker", values="volatility"))
    st.markdown("### Health Score Over Time")
    st.line_chart(eval_df.pivot(index="year", columns="ticker", values="overall_score"))

def show_sector_compare(df):
    st.markdown("## Sector Comparison")
    st.markdown("Compare financial health across sectors and companies.")
    st.divider()
    sectors = load_sectors()
    if not sectors:
        st.warning("Sector data not found.")
        return
    latest_df = df.sort_values("year").groupby("ticker").last().reset_index()
    latest_df["sector"] = latest_df["ticker"].map(sectors)
    latest_df = latest_df.dropna(subset=["sector"])
    st.markdown("### Average Health Score by Sector")
    sector_avg = latest_df.groupby("sector")["overall_score"].mean().round(2).sort_values(ascending=False)
    st.bar_chart(sector_avg)
    st.divider()
    st.markdown("### All Companies Ranked by Health Score")
    ranked = latest_df[["ticker", "sector", "overall_score", "profitability_score", "cashflow_score", "debt_score", "growth_score"]].sort_values("overall_score", ascending=False).reset_index(drop=True)
    ranked.index += 1
    st.dataframe(ranked)
    st.divider()
    st.markdown("### Filter by Sector")
    selected_sector = st.selectbox("Choose a sector", sorted(latest_df["sector"].unique()))
    sector_df = latest_df[latest_df["sector"] == selected_sector][["ticker", "overall_score", "profitability_score", "cashflow_score", "debt_score", "growth_score"]].sort_values("overall_score", ascending=False).reset_index(drop=True)
    sector_df.index += 1
    st.dataframe(sector_df)
    st.markdown(f"**Sector average: {sector_df['overall_score'].mean().round(2)} / 10**")

def show_ml_predictions():
    st.markdown("## ML Predictions")
    st.markdown("A Random Forest model trained on historical financial features predicts next year health scores.")
    st.divider()
    predictions = load_predictions()
    metrics = load_ml_metrics()
    if predictions is None:
        st.warning("Run src/ml_model.py first.")
        return
    if metrics:
        col1, col2, col3 = st.columns(3)
        col1.metric("Model", "Random Forest")
        col2.metric("MAE", metrics["rf_mae"])
        col3.metric("Training Samples", metrics["samples"])
        st.markdown("*MAE = Mean Absolute Error on a 0-10 scale. Lower is better.*")
        st.divider()
        st.markdown("### Feature Importance")
        importance_df = pd.DataFrame(metrics["feature_importance"]).sort_values("importance", ascending=False)
        st.bar_chart(importance_df.set_index("feature")["importance"])
        st.divider()
    st.markdown("### Predicted Next Year Scores")
    display = predictions.copy()
    display["trend"] = display["trend"].map({"Up": "↑ Up", "Down": "↓ Down", "Stable": "→ Stable"})
    display = display.sort_values("predicted_next_score", ascending=False).reset_index(drop=True)
    display.index += 1
    st.dataframe(display)

st.title("Financial Health Analyzer")
st.markdown("Get a plain-English financial health report for any major public company.")
page = st.radio("Select view", ["Company Report", "Compare", "Sector Compare", "ML Predictions", "Model Validation"], horizontal=True)
df = load_data()
if page == "Company Report":
    ticker_input = st.text_input("Enter a ticker symbol", placeholder="e.g. AAPL, MSFT, AMZN, NVDA, TSLA").upper().strip()
    if ticker_input:
        with st.spinner(f"Generating report for {ticker_input}..."):
            show_report(ticker_input, df)
elif page == "Compare":
    show_compare(df)
elif page == "Sector Compare":
    show_sector_compare(df)
elif page == "ML Predictions":
    show_ml_predictions()
elif page == "Model Validation":
    show_evaluation()
