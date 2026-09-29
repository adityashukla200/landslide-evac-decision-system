# System Architecture & Technical Specifications

> **Hyper-Local FlashFlood Prediction — SIH 2026, PS 26192**  
> Ministry of Home Affairs (MHA) / National Disaster Response Force (NDRF)

---

## 1. System Overview & Architecture Diagram

The system operates across **four coordinated layers**: Ingestion & Sensor Trust $\to$ Physics & Machine Learning $\to$ Evacuation Decision Engine $\to$ Multi-Channel Alerting Ladder, backed by an autonomous **ESP32 Edge Offline Loop**.

```mermaid
flowchart TD
    subgraph L1["Layer 1: Telemetry & Ingestion"]
        S1["25 Village IoT Nodes\n(Soil, Rain, Tilt, Stream)"] --> MQTT["MQTT Broker / In-Memory Bus"]
        EXT["IMD / Open-Meteo\nWeather Nowcast"] --> CACHE["Redis Cache & Fallback"]
        MQTT --> TRUST{"Sensor Trust Layer\n(Z-Score, Stuck, Consistency)"}
        TRUST -->|"Valid Readings"| VIRT["Virtual Sensor Interpolator\n(IDW + Orographic Kriging)"]
        TRUST -.->|"Spikes / Anomalies"| SUSPECT["Suspect Sensor Quarantine"]
    end

    subgraph L2["Layer 2: Physics & Predictive ML"]
        VIRT --> FEAT["Feature Engineering\n(Rain 1h/3h/24h/72h, Soil Sat)"]
        CACHE --> FEAT
        FEAT --> PHY["Geotechnical Physics Model\n(Infinite Slope Fs Calculation)"]
        FEAT --> XGB["Calibrated XGBoost Model\n(Isotonic Probability)"]
        PHY --> VA["Venn-Abers Conformal Calibrator\n90% Prediction Interval [P_lower, P_upper]"]
        XGB --> VA
        VA --> ANALOG["Historical Analog Matcher\n(Top-3 Kedarnath/Chamoli Events)"]
    end

    subgraph L3["Layer 3: Decision & Evacuation Intelligence"]
        VA --> TIER["Bayes-Optimal Threshold Engine\n(Loss Matrix: C_miss vs C_false_alarm)"]
        TIER --> IMPACT["Time-to-Impact Forecaster\n[min_minutes, likely_minutes]"]
        IMPACT --> ROUTER["NetworkX Evacuation Router\n(Cut-Risk Avoidance, Shelter Cap)"]
        ROUTER --> MARGIN["Available Margin Calculation\nMargin = T_impact - T_evacuate"]
    end

    subgraph L4["Layer 4: Multi-Channel Alert Ladder & UI"]
        MARGIN --> ORCH["Alert Ladder Orchestrator\n(CAP 1.2 XML Generator)"]
        ORCH --> CB["Cell Broadcast (Mock/TSP)"]
        CB --> SMS["SMS / WhatsApp (Mock/Twilio)"]
        SMS --> IVR["IVR Voice Call (Mock)"]
        IVR --> VOL["Volunteer Task Dispatch (Aapda Mitra)"]
        VOL --> SIREN["Hardware Siren Trigger (LoRa/RF)"]
        
        ORCH --> UI1["District Command Center\n(React 18 / MapLibre)"]
        ORCH --> UI2["Citizen PWA & Tourist Mode\n(Offline Manifest, Hindi/Eng)"]
    end

    subgraph EDGE["Autonomous Edge Node (Offline Loop)"]
        ESPSENS["ESP32-S3 Probes\n(Moisture, Tipping Rain, MPU6050)"] --> ESPFS["On-Device Factor of Safety"]
        ESPFS --> ESPDEC["Local Threshold Decider\n(WATCH / WARNING / EVACUATE)"]
        ESPDEC --> ESPSIR["120 dB Piezo Siren & LED Strip"]
        ESPDEC --> ESPLORA["Semtech SX1276 LoRa Broadcast\n(8-15 km Mountain Mesh Relay)"]
    end

    MQTT -.->|"Cloud Down (Kill Internet)"| EDGE
    style L1 fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#fff
    style L2 fill:#0f172a,stroke:#818cf8,stroke-width:2px,color:#fff
    style L3 fill:#0f172a,stroke:#fbbf24,stroke-width:2px,color:#fff
    style L4 fill:#0f172a,stroke:#34d399,stroke-width:2px,color:#fff
    style EDGE fill:#1e1b4b,stroke:#f87171,stroke-width:2px,color:#fff
```

---

## 2. Technical Layer Breakdown

### Layer 1: Multi-Source Telemetry & Sensor Trust
- **Simulated IoT Mesh**: 25 Himalayan villages in Uttarkashi/Chamoli. 18 villages equipped with 4 sensor streams (soil volumetric water content, rainfall accumulation, slope tilt, stream stage); 7 unequipped villages.
- **Sensor Trust Filter (`backend/app/services/sensors/trust.py`)**:
  - Rejects physical impossibilities ($S_v < 0$ or $> 1.0$, negative precipitation, tilt $> 10^\circ$).
  - Detects transient spikes via rolling Z-score ($|z| > 3.5$).
  - Flags frozen sensors where standard deviation over 8 cycles $< 10^{-5}$.
  - Excludes cross-sensor inconsistencies (e.g. cloudburst rainfall without commensurate soil moisture rise).
- **Virtual Sensor Interpolation (`backend/app/services/sensors/virtual.py`)**:
  - Uses Inverse Distance Weighting (IDW) with elevation lapse-rate adjustment:
    $$\text{factor} = 1.0 + 0.15 \times \left(\frac{\Delta \text{elevation}}{500\,\text{m}}\right)$$
  - Computes spatial uncertainty bounds ($\pm 1\sigma$) per unequipped settlement.

---

### Layer 2: Physics & Predictive ML Engine
- **Infinite-Slope Geotechnical Model (`ml/physics/slope_stability.py`)**:
  - Solves the Mohr-Coulomb limit equilibrium equation for saturated slopes:
    $$F_s = \frac{c' + (\gamma_{\text{sat}} - m \gamma_w) z \cos^2\beta \tan\phi'}{\gamma_{\text{sat}} z \sin\beta \cos\beta}$$
- **Calibrated Probabilistic Machine Learning (`ml/models/`)**:
  - Gradient-boosted ensemble (XGBoost) trained on multi-window rolling rainfall features ($1\text{h}, 3\text{h}, 6\text{h}, 24\text{h}, 72\text{h}$) with dual spatial and temporal holdout.
  - Isotonic post-hoc calibration reduces Expected Calibration Error (ECE) from $3.11\%$ to $0.044\%$.
- **Venn-Abers Conformal Calibration (`ml/uncertainty/conformal.py`)**:
  - Generates distribution-free, guaranteed valid prediction intervals $[p_{\text{lower}}, p_{\text{upper}}]$.

---

### Layer 3: Decision & Evacuation Routing
- **Bayes-Optimal Thresholds (`ml/decision/thresholds.py`)**:
  - Calculates operating points minimizing total expected loss:
    $$p^* = \frac{C_{\text{fa}}}{C_{\text{miss}} + C_{\text{fa}}}$$
  - Balances population vulnerability against economic disruption and false-alarm warning fatigue.
- **Topological Evacuation Router (`backend/app/services/evacuation.py`)**:
  - NetworkX pathfinding on the mountain trail and road network.
  - Severance risk penalties: Avoids road segments prone to debris fans or river undercutting.
  - Dynamically computes available evacuation margin:
    $$\text{Margin} = \text{Time-to-Impact} - \text{Time-to-Evacuate}$$
    Adjusts walking speed ($33.3\ \text{m/min}$) for elderly/vulnerable citizens and nighttime impedance ($+40\%$).

---

### Layer 4: Multi-Channel Alert Ladder & Delivery
- **CAP 1.2 XML Protocol (`backend/app/services/alerting/`)**:
  - Standardized OASIS Common Alerting Protocol generation with geofenced polygon tags.
- **Escalation Ladder**:
  - Cell Broadcast $\to$ SMS/WhatsApp $\to$ IVR Phone Call $\to$ Volunteer Handheld VHF Radio $\to$ LoRa Acoustic Siren.
  - 5-minute acknowledgement window before escalating to next tier.
- **Multilingual Messaging**:
  - Automated translation into English, Hindi, Garhwali, and Kumaoni under the 160-character cellular SMS limit.

---

## 3. Offline & Kill-Internet Resilience

When cellular backhaul, optical fiber, or cloud internet is severed by mountain debris flows:

1. **Hardware Edge Autonomy**:
   - ESP32-S3 microcontroller nodes continue sampling sensors locally every 5 minutes.
   - Computes local Factor of Safety ($F_s$) and threshold decisions directly on the node without internet.
2. **Autonomous Actuation**:
   - Fires high-intensity 120 dB piezo sirens and NeoPixel RGB alert lights immediately upon crossing critical thresholds.
3. **LoRa Mesh Broadcast**:
   - Broadcasts encrypted telemetry and alerts across a 915 MHz Semtech SX1276 radio mesh with 8–15 km mountain line-of-sight range.
   - Demonstrated in the Replay Engine: Maintains **78.5% population reach** even with 100% cloud internet severed.
