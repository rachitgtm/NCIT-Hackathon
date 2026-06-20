#!/usr/bin/env python3
"""
Admin panel for viewing tracked sentiment history.

Reads the CSV log written by sentiment_engine.py (one row per analyzed
message: timestamp, character_id, text, label, negative, neutral, positive)
and shows it as a filterable table plus a sentiment-over-time chart.

Usage:
  streamlit run admin.py

The log file path can be overridden with the SENTIMENT_LOG_PATH env var,
same as sentiment_engine.py, so both stay in sync.
"""

import os

import pandas as pd
import streamlit as st

LOG_PATH = os.environ.get("SENTIMENT_LOG_PATH", "sentiment_log.csv")

st.set_page_config(page_title="Sentiment Admin", layout="wide")
st.title("Sentiment Tracking — Admin Panel")


@st.cache_data(ttl=5)
def load_log(path):
    if not os.path.exists(path):
        return pd.DataFrame(columns=[
            "timestamp", "character_id", "text", "label",
            "negative", "neutral", "positive",
        ])
    df = pd.read_csv(path)
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df.sort_values("timestamp")


df = load_log(LOG_PATH)

if df.empty:
    st.info(f"No sentiment data logged yet at '{LOG_PATH}'. Send a message in the chat app to start tracking.")
    st.stop()

# --- Filters ---
col1, col2 = st.columns(2)

with col1:
    characters = sorted(c for c in df["character_id"].dropna().unique() if c)
    selected_characters = st.multiselect(
        "Filter by character", options=characters, default=characters,
    )

with col2:
    labels = sorted(df["label"].dropna().unique())
    selected_labels = st.multiselect(
        "Filter by sentiment label", options=labels, default=labels,
    )

filtered = df[
    df["character_id"].isin(selected_characters) & df["label"].isin(selected_labels)
] if selected_characters else df[df["label"].isin(selected_labels)]

# --- Summary metrics ---
m1, m2, m3, m4 = st.columns(4)
m1.metric("Messages tracked", len(filtered))
m2.metric("Avg positive", f"{filtered['positive'].mean():.2f}" if len(filtered) else "—")
m3.metric("Avg neutral", f"{filtered['neutral'].mean():.2f}" if len(filtered) else "—")
m4.metric("Avg negative", f"{filtered['negative'].mean():.2f}" if len(filtered) else "—")

# --- Chart: sentiment scores over time ---
st.subheader("Sentiment over time")
if len(filtered) > 0:
    chart_df = filtered.set_index("timestamp")[["negative", "neutral", "positive"]]
    st.line_chart(chart_df)
else:
    st.caption("No data matches the current filters.")

# --- Table: raw log ---
st.subheader("Message log")
st.dataframe(
    filtered.sort_values("timestamp", ascending=False),
    use_container_width=True,
    hide_index=True,
)

st.caption(f"Reading from `{LOG_PATH}`. Refreshes automatically every few seconds.")