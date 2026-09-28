# Early Warning System for Flash Floods & Landslides in Hilly Regions

> **Smart India Hackathon (SIH 2026) | Problem Statement 26192**  
> **Ministry of Home Affairs (MHA) / National Disaster Response Force (NDRF)**  
> **Pilot District:** Uttarkashi & Chamoli, Uttarakhand (Upper Bhagirathi & Alaknanda Basins)

[![Tests](https://img.shields.io/badge/Tests-167%20Passed-emerald.svg)](tests/)
[![Python](https://img.shields.io/badge/Python-3.11%20%7C%203.12%20%7C%203.13-blue.svg)](backend/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](backend/)
[![React](https://img.shields.io/badge/React-18.3%20%2B%20TypeScript-61dafb.svg)](frontend/)
[![License](https://img.shields.io/badge/License-MIT-gray.svg)](LICENSE)

An AI-assisted, multi-source disaster decision and evacuation intelligence platform designed for fragile Himalayan watersheds. It bridges the critical 3-to-8 hour lead-time gap between cloudburst onset and catastrophic debris flow impact.

---

## ⚡ Quickstart (Setup in < 5 Commands)

### Option A: Local Zero-Config Setup (< 5 Commands)

```bash
# 1. Set up Python environment & dependencies
python -m venv venv && .\venv\Scripts\activate && pip install -r requirements.txt

# 2. Seed database (25 pilot villages, shelters, road graph, and thresholds)
python scripts/seed_data.py

# 3. Launch Backend API Server (Port 8000)
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload

# 4. Launch Emergency Command Frontend (Port 5173)
cd frontend && npm install && npm run dev
```

Visit the dashboard at **`http://localhost:5173`** and backend Swagger docs at **`http://localhost:8000/docs`**.

---

### Option B: One-Command Live Evaluation

```bash
make demo
```
*Executes the automated end-to-end replay engine demonstrating **+7.0 hours extra lead time** over static thresholds and resilient **Kill-Internet local siren fallback**.*

---

### Option C: Docker Production Deployment

```bash
make up
```

---

## 🏔️ Core Innovations & Capabilities

1. **Physics-Guided Hybrid Prediction**:
   - Integrates regional numerical nowcasts with real-time geotechnical slope stability ($F_s$ infinite-slope model) and Venn-Abers conformal calibration.
   - Outputs calibrated failure probabilities with valid $90\%$ prediction intervals $[p_{\text{lower}}, p_{\text{upper}}]$.

2. **Dynamic Bayes-Optimal Thresholds**:
   - Cost-matrix optimization balancing the asymmetric human cost of missed landslides ($C_{\text{miss}}$) against evacuation disruption and warning fatigue ($C_{\text{fa}}$).
   - Generates tailored, audit-logged thresholds per settlement rather than blunt statewide rainfall cutoffs.

3. **Autonomous Evacuation Router**:
   - NetworkX topological graph routing between 25 mountain villages and safe shelters.
   - Dynamically avoids high cut-risk road segments and re-routes around severed gorges.
   - Adjusts for vulnerable population walking speeds and night-time impedance.

4. **Multi-Channel Alert Ladder & Fatigue Control**:
   - Automated escalation: Cell Broadcast $\to$ SMS $\to$ IVR Call $\to$ Field Volunteer Radio $\to$ Offline Siren.
   - CAP 1.2 XML compliant notifications in English, Hindi, Garhwali, and Kumaoni ($\le 160$ characters).
   - Confirmed-safe geofencing and tier cooldown preventing alert fatigue.

5. **Kill-Internet Edge Resilience**:
   - ESP32-S3 MicroPython firmware with autonomous local thresholding.
   - LoRa 915 MHz peer-to-peer relay and hardware piezo siren triggers when cloud connection or cellular networks drop.

---

## 📂 Documentation Directory

| Document | Description |
|---|---|
| [**ARCHITECTURE.md**](docs/ARCHITECTURE.md) | System architecture, data flow, 4-tier pipeline, and full Mermaid diagram |
| [**RESULTS.md**](docs/RESULTS.md) | Real computed benchmark metrics, calibration curves, and honest model limitations |
| [**DATA.md**](docs/DATA.md) | Real administrative geographic anchors vs. synthetic sensor telemetry demarcation |
| [**API.md**](docs/API.md) | Complete OpenAPI/REST specification and MQTT topic definitions |
| [**DEMO_SCRIPT.md**](docs/DEMO_SCRIPT.md) | Structured 5-minute presentation script for evaluators and NDRF commanders |
| [**edge.md**](docs/edge.md) | ESP32-S3 MicroPython edge firmware, local $F_s$ math, actuators, and wiring specs |
| [**FRONTEND.md**](docs/FRONTEND.md) | 14-page emergency command portal architecture and offline PWA implementation |

---

## 🔒 Security, Privacy & Compliance (DPDP Act 2023)

- **Role-Based Access Control (RBAC)**: Enforces `officer`, `volunteer`, and `citizen` privilege boundaries.
- **PII Protection**: Citizen and volunteer telephone numbers, personal identities, and exact domestic coordinates are masked by default (`+91 98*** **210`).
- **DDoS & Flooding Protection**: Sliding-window IP rate limiting (180 requests/min) across all API endpoints with `X-RateLimit-*` headers.

---

## ⚠️ Limitations & Future Work

While architected for immediate field testing, operational state-level rollout requires:
1. **Real IMD & SDMA API Integration**: Replacing Open-Meteo and synthetic nowcasts with direct Indian Meteorological Department (IMD) DWR (Doppler Weather Radar) and Uttarakhand State Disaster Management Authority (USDMA) hydrological feeds.
2. **National CAP & Telecom Gateway**: Transitioning from simulated channel adapters to the government C-DOT / NDMA Common Alerting Protocol server and telecom service provider (TSP) cell broadcast towers.
3. **In-Situ Geotechnical Instrumentation**: Field-calibrating infinite-slope soil shear strength parameters ($c', \phi'$) using borehole core samples from chronically unstable slopes (e.g. Bhatwari, Helang).
