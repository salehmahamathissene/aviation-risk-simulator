import streamlit as st
import requests


def get(url):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except requests.JSONDecodeError:
                detail = response.text
            return {
                "error": "validation" if response.status_code == 422 else "http",
                "status_code": response.status_code,
                "detail": detail,
            }
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return {"error": "timeout", "detail": "The API request timed out."}
    except requests.RequestException:
        return {"error": "connection", "detail": "API is not running or unreachable."}


def post(url, payload):
    try:
        response = requests.post(url, json=payload, timeout=10)
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except requests.JSONDecodeError:
                detail = response.text
            return {
                "error": "validation" if response.status_code == 422 else "http",
                "status_code": response.status_code,
                "detail": detail,
            }
        response.raise_for_status()
        return response.json()
    except requests.Timeout:
        return {"error": "timeout", "detail": "The API request timed out."}
    except requests.RequestException:
        return {"error": "connection", "detail": "API is not running or unreachable."}


def display_api_error(data):
    if data.get("error") == "connection":
        st.error(data["detail"])
    elif data.get("error") == "timeout":
        st.warning(data["detail"])
    elif data.get("error") == "validation":
        st.error(
            f"Validation error (HTTP {data['status_code']}): {data['detail']}"
        )
    else:
        st.error(
            f"API HTTP error (HTTP {data.get('status_code', 'unknown')}): "
            f"{data['detail']}"
        )


st.title("✈️ Airline Disruption Intelligence Dashboard")

if st.button("Run Global Simulation"):
    data = get("http://127.0.0.1:8000/simulate/real")

    if "error" in data:
        display_api_error(data)
    else:
        st.subheader("📊 Global Metrics")

        c1, c2, c3 = st.columns(3)
        c1.metric("Mean Delay", round(data["mean_delay"], 2))
        c2.metric("P95 Delay", round(data["p95_delay"], 2))
        c3.metric("Cancellations", data["cancelled_flights"])

        st.metric("💰 Economic Loss ($)", int(data["economic_loss_usd"]))


if st.button("Run Network Simulation"):
    net = post(
        "http://127.0.0.1:8000/simulate/network",
        {"runs": 500, "start_airport": "CDG", "initial_delay": 60},
    )

    if "error" in net:
        display_api_error(net)
    else:
        st.subheader("🌍 Network Impact")

        st.metric("Mean Network Delay", round(net["mean_network_delay"], 2))
        st.metric("P95 Network Delay", round(net["p95_network_delay"], 2))
        st.metric("Max Delay", round(net["max_delay"], 2))
        st.write("Affected Airports", ", ".join(net["affected_airports"]))
