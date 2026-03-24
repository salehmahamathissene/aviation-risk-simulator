# ✈️ Airline Network Disruption Simulation Engine

A simulation-driven backend system for modeling airline disruptions, delay propagation, and economic risk.

---

## 🚀 Overview

This project models how local disruptions (delays, congestion, weather) propagate across an airline network and impact operations and revenue.

Instead of reacting to disruptions, the system simulates them *before they happen*.

---

## ⚙️ Core Capabilities

- 🌐 Graph-based airline network modeling (NetworkX)
- 📊 Monte Carlo simulation (thousands of runs)
- ⏱️ Delay propagation across connected flights
- ❌ Cancellation modeling under stress scenarios
- 💸 Economic loss estimation (passenger impact + compensation)
- ⚠️ Risk classification (LOW / MEDIUM / HIGH)

---

## 🧠 System Architecture

- **FastAPI** → simulation engine (API layer)
- **NetworkX** → flight network graph
- **NumPy / Pandas** → stochastic modeling
- **PyVis** → network visualization
- **Event-based logic** → delay propagation

---

## 📊 Example Output

```json
{
  "mean_delay": 45,
  "p95_delay": 68,
  "cancelled_flights": 400,
  "economic_loss_usd": 20000000,
  "risk_level": "HIGH"
}
