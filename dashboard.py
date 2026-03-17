import streamlit as st
import requests
import pandas as pd


def get(url):
    try:
        return requests.get(url).json()
    except:
        return {"error": "API not running"}


st.title("✈️ Airline Disruption Intelligence Dashboard")

if st.button("Run Global Simulation"):
    data = get("http://127.0.0.1:8000/simulate/real")

    if "error" not in data:
        st.subheader("📊 Global Metrics")

        c1, c2, c3 = st.columns(3)
        c1.metric("Mean Delay", round(data["mean_delay"], 2))
        c2.metric("P95 Delay", round(data["p95_delay"], 2))
        c3.metric("Cancellations", data["cancelled_flights"])

        st.metric("💰 Economic Loss ($)", int(data["economic_loss_usd"]))


if st.button("Run Network Simulation"):
    net = get("http://127.0.0.1:8000/simulate/network")

    if "error" not in net:
        st.subheader("🌍 Network Impact")

        st.metric("Mean Network Delay", round(net["mean_network_delay"], 2))
        st.metric("P95 Network Delay", round(net["p95_network_delay"], 2))
        st.metric("Max Delay", round(net["max_delay"], 2))
