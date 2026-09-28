# Early Warning System for Flash Floods & Landslides in Hilly Regions

> **Smart India Hackathon (SIH 2026) | Problem Statement 26192**  
> **Ministry of Home Affairs (MHA) / National Disaster Response Force (NDRF)**  
> **Pilot District:** Uttarkashi & Chamoli, Uttarakhand

For detailed architecture, evaluation reports, and live demo instructions, see [**docs/README.md**](docs/README.md).

---

## ⚡ Quickstart (Setup in < 5 Commands)

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

---

## 🚀 One-Command Evaluator Demo

```bash
make demo
```
*Runs the full end-to-end replay engine demonstrating **+7.0 hours extra lead time** and **Kill-Internet local siren fallback**.*

---

## 📂 Documentation Directory

- [**docs/ARCHITECTURE.md**](docs/ARCHITECTURE.md) — System Architecture & Mermaid Diagram
- [**docs/RESULTS.md**](docs/RESULTS.md) — Benchmark Metrics, Calibration Curves & Honest Limitations
- [**docs/DATA.md**](docs/DATA.md) — Real Geographic Anchors vs Synthetic Telemetry
- [**docs/API.md**](docs/API.md) — REST & MQTT API Reference
- [**docs/DEMO_SCRIPT.md**](docs/DEMO_SCRIPT.md) — 5-Minute Evaluator & Judge Demo Script
- [**docs/edge.md**](docs/edge.md) — ESP32 MicroPython Firmware, Pinouts & Offline LoRa Specs
