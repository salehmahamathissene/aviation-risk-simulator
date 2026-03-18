# ✈️ Aviation Risk Simulation Engine

A next-level backend system that models airline disruptions using:

- Graph-based network modeling (NetworkX)
- Monte Carlo simulation
- Delay propagation algorithms
- Economic impact estimation

## 🚀 Features

- Simulates global airline network disruptions
- Models cascading delays across airports
- Estimates cancellations and financial losses
- Provides API endpoints for real-time analysis

## 🧠 Tech Stack

- Python (FastAPI)
- NetworkX (graph modeling)
- NumPy / Pandas (data simulation)
- PyVis (network visualization)

## 📊 Example Output

```json
{
  "mean_delay": 45,
  "p95_delay": 68,
  "cancelled_flights": 400,
  "economic_loss_usd": 20000000,
  "risk_level": "HIGH"
}
