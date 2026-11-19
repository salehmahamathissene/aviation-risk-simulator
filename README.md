# ✈️ Airline Network Disruption Simulation Engine

A Python-based simulation project exploring airline network disruptions, stochastic delay modeling, cancellation scenarios, and estimated operational costs.

## 🚀 Overview

Airline disruptions can propagate beyond the flight where they originate. Delays, cancellations, and network dependencies can affect subsequent operations and increase operational costs.

This project explores these effects through simulation, using probabilistic modeling and airline network concepts to study potential disruption scenarios.

The objective is to examine how simulated disruptions affect delay distributions, cancellation counts, and estimated economic impact.

## ⚙️ Implemented Capabilities

- **Monte Carlo simulation:** Repeated stochastic simulations using configurable run counts.
- **Delay modeling:** Random delay generation using input dataset parameters.
- **Cancellation modeling:** Probabilistic cancellation sampling.
- **Statistical analysis:** Mean delay and 95th-percentile delay calculations.
- **Economic estimation:** Simplified cost estimation based on simulated delays and cancellations.
- **FastAPI service:** HTTP endpoints for accessing simulation results.
- **Network simulation modules:** Separate modules exploring graph-based airline networks and delay propagation.

## 🧠 Technology Stack

| Technology | Purpose |
|---|---|
| Python | Core implementation |
| FastAPI | API layer |
| NumPy | Random sampling and numerical calculations |
| Pandas | Input data processing |
| NetworkX | Airline network modeling modules |
| Streamlit | Dashboard prototype |

## 🏗️ Architecture

The project is organized around several engineering components:

- **API layer:** Exposes simulation functionality through FastAPI.
- **Monte Carlo engine:** Executes repeated stochastic simulations.
- **Network modeling:** Represents airline relationships using graph-based structures.
- **Disruption propagation:** Explores how delays can affect connected flights.
- **Economic analysis:** Estimates simplified financial impacts.

The current API exposes the global Monte Carlo implementation. Other network and dashboard components remain under development.

## 📊 Simulation Output

The active simulation endpoint returns metrics including:

- `mean_delay`
- `p95_delay`
- `cancelled_flights`
- `economic_loss_usd`
- `runs`

Results are generated from the project's local CSV dataset and stochastic model. They are experimental estimates, not live operational forecasts.

## ▶️ Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/salehmahamathissene/aviation-risk-simulator.git
cd aviation-risk-simulator
```

### 2. Create a virtual environment

**Windows PowerShell**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Run the API

```bash
uvicorn app.main:app --reload
```

Open:

- API: http://127.0.0.1:8000
- Interactive API documentation: http://127.0.0.1:8000/docs

### 5. Execute a simulation

```bash
curl http://127.0.0.1:8000/simulate/global
```

The simulation currently defaults to 2,000 runs.

## ⚠️ Scope and Limitations

This is an experimental engineering project.

- The current input dataset is illustrative and limited in size.
- The `/simulate/real` endpoint currently uses the same simulation implementation as `/simulate/global`; it does not retrieve live airline data.
- Network simulation modules are separate from the currently exposed API endpoints.
- Economic estimates use simplified assumptions rather than validated airline cost models.
- The project has not been established as a certified or operational airline decision-support system.

Simulation results should not be used for actual dispatch, safety, financial, or regulatory decisions.

## 🔭 Future Development

Potential areas for further development include:

- Historical flight-data integration.
- More detailed aircraft rotation and schedule modeling.
- Improved delay propagation and recovery strategies.
- Model calibration and validation.
- Interactive network visualization.
- More realistic operational and economic assumptions.

## 👨‍💻 Author

**Saleh Mahamat**

Software Engineering Student | Backend & Full-Stack Developer | Aviation Technology

GitHub: https://github.com/salehmahamathissene

Project repository: https://github.com/salehmahamathissene/aviation-risk-simulator
