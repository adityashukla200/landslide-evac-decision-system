# 5-Minute Evaluator & Judge Presentation Script

> **SIH 2026 Problem Statement 26192**  
> Early Warning System for Flash Floods & Landslides in Hilly Regions  
> **Audience:** NDRF Commanders, District Disaster Management Authorities (DDMA), Technical Jury  
> **Time Limit:** Exactly 5 Minutes

---

## Quick Reference Setup (Before Demo Starts)

Ensure two terminal windows and one browser window are open:
1. **Terminal 1**: Backend running (`python -m uvicorn backend.app.main:app --port 8000`)
2. **Terminal 2**: Ready for CLI commands (`c:\Users\shukl\OneDrive\Desktop\PS192`)
3. **Browser**: Open to `http://localhost:5173` (Command Center) & `http://localhost:5173/tourist` (Char Dham Tourist Mode)

---

## ⏱️ Chronological 5-Minute Walkthrough

### Minute 0:00 – 1:00 | The Problem & Architectural Vision
**Speaker:**
> *"Respected Jury members, in Uttarakhand’s high-altitude valleys, catastrophic debris flows and flash floods occur in narrow 2-to-4 hour windows following localized cloudbursts.  
> Traditional systems rely on static regional rainfall thresholds—such as 50 mm/hr or 200 mm/24h. These static triggers suffer from a deadly dilemma: either they fire 24 hours too early causing community warning fatigue, or they fire after the road has already collapsed.  
> For SIH 26192, we built an AI-assisted disaster management and evacuation intelligence platform covering 25 settlements across Uttarkashi and Chamoli. It combines four innovations: physical slope stability, conformal uncertainty bands, dynamic evacuation routing, and an offline-resilient edge fallback."*

**Action:** Show the **Live Risk Map** on the dashboard (`http://localhost:5173/live-map`), highlighting the upper Bhagirathi valley settlements from Bhatwari to Harsil.

---

### Minute 1:00 – 2:00 | Sensor Trust Layer & Physics Engine
**Speaker:**
> *"First, mountain IoT networks are notoriously unreliable. Probes get covered in silt, freeze, or suffer power dropouts.  
> In our sensor trust layer, raw telemetry passes through 5 quality checks before reaching the ML model: physical range bounds, rolling Z-score outlier filtering, stuck sensor detection, and cross-sensor physical consistency. For instance, if a rain gauge reports heavy cloudburst rainfall but the soil moisture probe shows zero infiltration, the trust layer flags the pair as suspect and quarantines them.  
> For villages without physical sensors, our virtual interpolator estimates volumetric water content using Inverse Distance Weighting with terrain elevation lapse-rate adjustments.  
> Concurrently, our geotechnical module solves the infinite-slope stability equation in real time, calculating the Factor of Safety $F_s$ based on regolith depth, slope angle, and saturation."*

**Action:**
- Switch to the **Sensors Page** (`http://localhost:5173/sensors`).
- Point out the trust status badges (`OK`, `SUSPECT`, `DEGRADED`) and the virtual sensor estimates for unequipped villages (`Gamri`, `Tiloth`).

---

### Minute 2:00 – 3:00 | Calibrated ML, Conformal Bounds & Evacuation Margins
**Speaker:**
> *"Next is our predictive intelligence. An XGBoost model trained on multi-window rolling rainfall features is post-hoc calibrated using Isotonic Regression, reducing Expected Calibration Error from 3.11% to 0.044%.  
> Crucially, for life-critical evacuation decisions, point estimates are not enough. We implement Venn-Abers conformal calibration, producing a mathematically valid 90% prediction interval $[P_{\text{lower}}, P_{\text{upper}}]$. Evacuation orders are only triggered when the conformal lower bound exceeds the Bayes-optimal threshold, slashing false evacuations by over 34%.  
> Our routing engine calculates:
> $$\text{Available Margin} = \text{Time-to-Impact} - \text{Time-to-Evacuate}$$
> It factors in vulnerable walking speeds ($33.3\ \text{m/min}$), night-time hazards, and dynamically routes evacuees away from severed mountain roads toward high-ground shelters with verified capacity."*

**Action:**
- Navigate to **Evacuation Planning** (`http://localhost:5173/evacuation`).
- Select **Bhatwari**; show the available margin calculation (e.g. 40 minutes) and route selection diverting from severed Highway Route A to Ridge Path B.

---

### Minute 3:00 – 4:00 | Multi-Channel Alert Ladder & Tourist PWA
**Speaker:**
> *"When an alert triggers, our system dispatches standardized OASIS CAP 1.2 XML messages across a 5-step escalation ladder: Cell Broadcast, SMS, IVR automated voice calls, field volunteer task cards, and local acoustic sirens.  
> To protect local communities from alert fatigue, we enforce cooldown periods and suppress re-broadcasts to citizens in confirmed safe zones.  
> Messages are automatically generated in English, Hindi, Garhwali, and Kumaoni under the strict 160-character SMS limit.  
> For pilgrims visiting Kedarnath or Gangotri, our standalone Tourist Mode provides live bilingual safety status, safe havens, and emergency SOS dials even in offline PWA cache."*

**Action:**
- Show the **Alerts Page** (`http://localhost:5173/alerts`) displaying the CAP 1.2 XML preview and multi-channel acknowledgement reach percentages.
- Quickly show the **Tourist Mode** portal (`http://localhost:5173/tourist`) with the Hindi toggle and offline banner.

---

### Minute 4:00 – 4:45 | The Climax: Replay Demo & "Kill Internet" Switch
**Speaker:**
> *"Finally, we present our disaster replay demonstration. What happens when a cloudburst severs the optical fiber and cellular towers?  
> Let us run our calibrated replay script with the Kill-Internet switch engaged."*

**Action:** In **Terminal 2**, run:
```bash
python scripts/replay_demo.py --scenario bhatwari_debris_flow_synthetic --kill-internet
```

**Speaker points to the terminal output:**
> *"Observe these verified numbers:  
> 1. Our AI Early Warning System issues the first advisory at **T - 12 Hours**, whereas the IMD static rainfall threshold doesn't breach until **T - 5 Hours**. That is **+7.0 HOURS OF EXTRA ACTIONABLE LEAD TIME**.  
> 2. Look at the channels: With internet severed, Cell Broadcast, SMS, and IVR are down. Yet, our autonomous ESP32 edge node fires the local 120 dB piezo siren and dispatches Aapda Mitra volunteers over 915 MHz LoRa mesh radio, achieving a **78.5% citizen evacuation reach** with zero cloud connectivity!"*

---

### Minute 4:45 – 5:00 | Security, Compliance & Future Roadmap
**Speaker:**
> *"In compliance with the Digital Personal Data Protection (DPDP) Act 2023, all citizen phone numbers and domestic locations are masked across all portals. The API is fortified with Role-Based Access Control and rate limiting.  
> While currently calibrated on 25 synthetic and public disaster events, the architecture is ready for direct integration with IMD Doppler radar grids and NDMA's live Cell Broadcast gateway.  
> Thank you, and we welcome your questions."*

---

## 🎯 Anticipated Jury Questions & Ready Answers

**Q1: Is this real or simulated sensor data?**
> *"All sensor telemetry, IoT nodes, and rainfall streams are synthetic physics-calibrated simulations anchored to real administrative coordinates, elevations, and road topologies of Uttarkashi and Chamoli. In accordance with strict transparency, every synthetic record is labeled `is_synthetic: true`."*

**Q2: How does the edge node calculate Factor of Safety without the cloud?**
> *"The ESP32-S3 runs a lightweight MicroPython implementation of the infinite-slope equation taking ADC soil moisture readings and MPU-6050 tilt angles directly, deciding WATCH, WARNING, or EVACUATE in under 5 milliseconds locally."*

**Q3: How do you prevent false alarm panic?**
> *"We use Bayes-optimal thresholding tailored to individual village loss ratios and gate evacuation orders with Venn-Abers conformal lower bounds. In our benchmarks, this cut annual evacuation false alarms from 32 down to 8.8 hours per village per year."*
