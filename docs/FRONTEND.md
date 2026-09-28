# SIH 26192 — Disaster EWS Frontend Architecture & User Guide

**System:** AI-Assisted Hilly-Region Flash Flood & Landslide Early Warning & Evacuation System  
**Pilot Catchment:** Uttarkashi District (Upper Bhagirathi & Yamuna Basins), Uttarakhand  
**Target Roles:** NDRF Commandants, District Magistrates / Officers, Field Volunteers (Aapda Mitra), Citizens & Char Dham Pilgrims.

---

## 1. Product Vision & Operating Philosophy

The frontend is an **emergency decision and action platform**, not an analytical dashboard.
Every screen is optimized for high-stress, low-connectivity disaster operations adhering to the six-stage directive cycle:

$$\text{DETECT} \longrightarrow \text{UNDERSTAND} \longrightarrow \text{DECIDE} \longrightarrow \text{ALERT} \longrightarrow \text{EVACUATE} \longrightarrow \text{VERIFY}$$

---

## 2. Core Experience Layers

### A. Emergency Command Center (Desktop / Tablet)
* **Live Catchment Risk Map (`/map`, `/`)**: Interactive MapLibre GL geospatial map of 25 Uttarkashi catchment settlements (Harsil, Bhatwari, Maneri, Joshiyara, Barkot, Purola). Displays real-time risk tiers (Safe, Watch, Warning, Evacuate), pulsating hazard glows, rain gauge telemetry, and terrain contours.
* **Village Intelligence Drawer (`VillageDetailPanel`)**:
  * **"Why This Alert Fired" Explainability Engine**: Plain-language breakdown of primary hazard drivers (e.g. 72h cumulative rainfall exceeding 180 mm, Factor of Safety $< 1.15$, soil saturation $> 88\%$).
  * **Conformal Uncertainty $[p_{\text{lower}}, p_{\text{upper}}]$**: Rare-event Venn-Abers calibration intervals.
  * **Historical Analog Match**: Most similar past disaster event with similarity percentage and meteorological hyetograph comparison.
  * **Time-to-Impact vs Time-to-Evacuate**: Operational lead time margin calculation.
* **Multi-Channel Alert Dispatch (`/alerts`)**:
  * Broadcast authoring with automatic character counter ($\le 160$ chars) and Hindi/English templates.
  * Audio synthesis preview (TTS) for siren and IVR pre-listening.
  * Two-step error prevention modal with resident impact summary.
  * Visual 5-step fallback ladder tracking: $\text{Cell Broadcast} \to \text{SMS} \to \text{IVR Call} \to \text{Aapda Mitra Task} \to \text{Siren Trigger}$.
  * CAP 1.2 XML compliant inspector.
* **Dynamic Evacuation Routing & Shelters (`/evacuation`, `/shelters`)**:
  * Cut-risk analysis on mountain road segments avoiding flooded culverts and debris flow tracks.
  * Refuge shelter capacity, current occupancy, and live utility status (power, water, medical post).
* **Sensor Network & Multi-Source Trust (`/sensors`)**:
  * Real-time rain gauges, water level radar, piezometers, and tiltmeters.
  * Multi-sensor cross-validation and fault/drift detection.
* **Field Volunteers & Vulnerable Registry (`/volunteers`, `/vulnerable`)**:
  * Aapda Mitra task dispatch with 1-click status transitions (`PENDING` $\to$ `ACCEPTED` $\to$ `IN PROGRESS` $\to$ `COMPLETED`).
  * Registry for elderly, mobility-impaired, pregnant women, and infants with contact and evacuation assistance tags.
* **What-If Scenario Simulator (`/simulator`) & Event Replay (`/replay`)**:
  * Real-time perturbation sliders for Rainfall $+100\%$, Soil Saturation $+50\%$, and Upstream Inflow $+100\%$.
  * Historical disaster timeline scrubber ($T-12\text{h} \to \text{EVENT}$) for training and post-event audits.
* **Crowdsourced Community Reports (`/reports`)**:
  * Citizen ground-truth reports with GPS, photo upload, and verification workflow.
* **System Health & Observability (`/health`)**:
  * Live status of FastAPI, PostgreSQL/PostGIS, Redis, MQTT broker, and ML inference latency.

---

### B. Citizen Emergency PWA (`/citizen`)
* **3-Second Comprehension**:
  * Giant semantic status card: **SAFE (Green) / WATCH (Yellow) / WARNING (Orange) / EVACUATE NOW (Pulsing Red)**.
  * Never relies on color alone — uses universal icons, bold text, and multilingual audio.
* **Actionable Emergency Directive**:
  * Exact instruction: *"Leave now. Take Route B to Shelter 2. You have 38 minutes."*
* **1-Tap Voice Stream**:
  * High-priority text-to-speech announcement in Hindi and English.
* **1-Tap Offline Emergency Navigation**:
  * Step-by-step route to nearest high ground with distance and walking time.
* **1-Tap SOS Distress Call**:
  * Direct dial for 112 (National Emergency), 1077 (District Disaster Room), 1070 (SEOC).
* **Offline First Resilience**:
  * Registered Service Worker (`/sw.js`) and Web App Manifest (`/manifest.json`) caching critical guidance when mobile towers go down.

---

### C. Char Dham Tourist & Pilgrim Safety Portal (`/tourist`)
* **Highway & Sector Status**: NH-34 (Gangotri Route), NH-134 (Yamunotri Route), and Harsil-Gangotri sector alerts.
* **Himalayan Safety Rules**: Guidelines for pilgrims navigating hilly terrain, cloudburst warnings, and torrential stream crossings.
* **Refuge Finder**: Direction and elevation metrics to nearest high-ground tourist complexes and government shelters.

---

## 3. SIH Evaluator 5-Minute Demo Flow

The global **ScenarioBar** mounted at the top of the Command Center allows instant 1-click stage progression for judges:

| Step | Scenario | Description | Key Visuals |
|---|---|---|---|
| **1** | **Normal** | Baseline monsoon conditions | All villages Green/Safe, low rain, stable slopes ($F_s > 1.4$). |
| **2** | **Heavy Rain** | Cloudburst upstream | Gauges jump to $45\text{ mm/h}$, Watch alerts trigger on Harsil & Bhatwari. |
| **3** | **Landslide Warning** | Slope instability detected | Maneri $F_s$ drops to $1.12$, Orange Warning card, analog match shown. |
| **4** | **Flash Flood** | Bhagirathi river surges | Maneri & Bhatwari turn Red/Evacuate, 5-step fallback ladder activates. |
| **5** | **Evacuation Active** | Coordinated evacuation | Volunteer cards dispatched, route cut-risk flags active, Citizen PWA in Evacuate mode. |

---

## 4. Frontend Technology Stack
- **Framework**: React 18 with TypeScript
- **Bundler**: Vite 5
- **Styling**: Tailwind CSS 3 with Custom Emergency Disaster Palette
- **Routing**: React Router v6
- **Maps**: MapLibre GL JS v4
- **Icons**: Lucide React
- **PWA**: Custom Offline Cache Service Worker + Web App Manifest
