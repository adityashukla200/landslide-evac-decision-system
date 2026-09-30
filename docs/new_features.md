# Advanced Architectural Features: Hyper-Local FlashFlood Prediction Platform

This document provides a comprehensive technical reference for the enterprise-grade disaster management systems implemented across all six core dimensions.

---

## 1. Advanced AI / Computer Vision & Satellite Remote Sensing

### A. Citizen Media Computer Vision Pipeline (`backend/app/services/ai_cv/pipeline.py`)
- **Floodwater Segmentation (`FloodwaterSegmenter`)**:
  - Employs color space transformations (turbid silt $R > B \times 0.98$, foaming water specular reflection, vegetation exclusion $G > R \times 1.2$).
  - Quantifies `water_fraction` $\in [0.0, 1.0]$, extracts normalized bounding regions, and computes silt/foam turbidity metrics.
- **Staff Gauge & Inundation Depth Estimation (`StaffGaugeReader`)**:
  - Sobel-style horizontal gradient filtering detects vertical structures (bridge piers, staff gauges, curbs).
  - Non-linear empirical depth scaling calibrated to Himalayan river channels.
- **Debris Flow / Torrent Surface Velocity (`DebrisVelocityEstimator`)**:
  - Multi-frame optical flow displacement calculates flow velocity ($0$ to $7.5\text{ m/s}$) and classifies flow regime (`SUPERCRITICAL_DEBRIS_TORRENT`, `ACTIVE_FAST_CURRENT`, `SLOW_INUNDATION`, `STAGNANT_PONDING`).
- **False-Alarm Rejection (`FalseAlarmClassifier`)**:
  - Variance and chromatic balance filtering flags indoor domestic lighting, zero-variance blank screens, or dry sunny pavement.
- **Unified Orchestration (`CVOrchestrator`)**:
  - Async FastAPI endpoints (`POST /api/v1/cv/analyze` and `POST /api/v1/cv/analyze/{report_id}`) execute pipeline and persist predictions to `citizen_reports` table.

### B. Catchment GNN & PINN Hydrodynamic Runoff Engine (`backend/app/services/ai_cv/gnn_runoff.py`)
- Directed Acyclic Graph (DAG) topology mapping the Upper Bhagirathi river basin from Harsil (`VIL_UTK_01`) down to Chinyalisaur (`VIL_UTK_14`).
- **Graph Neural Network (GNN)** message-passing aggregates kinematic wave discharge $Q(t)$ along 13 channel reaches.
- **Physics-Informed Neural Network (PINN) Residual Correction**:
  - Enforces mass conservation and calculates downstream pore-pressure convergence penalty $\Delta F_s \in [0.0, 0.35]$.
  - Corrects 1D Infinite Slope Factor of Safety ($F_s$), flagging unstable valley toe slopes where $F_s < 1.0$.

### C. Satellite Remote Sensing & Cloudburst Nowcasting (`backend/app/services/satellite/providers.py`)
- **Sentinel-1 SAR / InSAR**: Phase coherence loss and Line-of-Sight (LOS) downslope deformation velocity ($\text{mm/year}$) tracking slow-creeping slopes.
- **Sentinel-2 MSI Optical**: Modified Normalized Difference Water Index (MNDWI) surface water extent and bare landslide scar delineation.
- **NASA GPM IMERG**: Half-hourly calibrated precipitation nowcast ($\text{mm/h}$) and 3-hour rainfall accumulation.
- **INSAT-3D/3DR Rapid-Scan Cloudburst Precursor**:
  - Monitors Thermal Infrared (TIR-1, $10.8\ \mu\text{m}$) cloud-top cooling rate.
  - Critical convective updraft threshold: $\Delta T_b / \Delta t < -15\text{ K / 15 min}$ and $T_b \le -65^\circ\text{C}$ triggers a high-priority Cloudburst Precursor Alert ($15-30$ minute advance lead time).
- **Satellite Risk Fusion Engine**: Integrates multi-sensor satellite anomalies into calibrated village risk.

---

## 2. IoT, Hardware & Multi-Hop Edge Mesh

### A. LoRaWAN / Meshtastic Edge Mesh (`backend/app/services/mesh/lora_packet.py`)
- **Binary Codec for SX1262 / RAK4631**:
  - 16-byte packed frame: Magic byte `0x51`, Packet Type, 16-bit Node IDs, Hop Count, Status Flags, Soil Moisture, River Stage, Rain Rate, Battery %, and ATM CRC-8 checksum.
- **Store-and-Forward Mesh Gateway**:
  - De-duplicates packets across mesh repeaters and buffers telemetry during cellular blackouts, bridging to MQTT upon uplink restoration.

### B. Acoustic & Geophone GLOF Early Warning (`backend/app/services/mesh/infrasound_glof.py`)
- Ingests SM-24 class geophone and MEMS infrasound streams ($1 - 30\text{ Hz}$ band).
- TinyML spectral analysis tracks energy concentration in the $1.5 - 12\text{ Hz}$ GLOF rumble band.
- Multi-window persistence with peak acoustic pressure $\ge 2.5\text{ Pa}$ triggers automated edge siren activation and mesh broadcast $15-30$ minutes before downstream river stage surge.

### C. Solar MPPT & Sub-Zero Battery Strategy (`backend/app/services/mesh/solar_power.py`)
- Sub-zero protection halts LiFePO4 charging when $T_{\text{battery}} < 0^\circ\text{C}$ to prevent dendritic lithium plating and cell shorting.
- Adaptive deep-sleep duty cycling scales sleep intervals from 60s to 900s during critical power states ($<15\%$).
- Dispatches emergency `LAST_GASP` mesh packet before node brownout.

---

## 3. Dynamic Evacuation Routing & Shelter Balancing

### A. Multi-Modal Graph & Dynamic Edge Blocking (`backend/app/services/routing/dynamic_graph.py`)
- Multi-modal network supporting Pedestrian Mountain Trails, 4x4 Jeep Roads, and Helicopter Landing Zones (HLZ).
- Dynamic edge cutoffs: If river stage exceeds bankfull capacity or landslide runout intersects a reach, edge weight becomes $\infty$.
- Time-dependent cost function: $W = T_{\text{base}} \times (1.0 + 2.5 \times \text{HazardScore})$.

### B. Real-Time Shelter Capacity Balancing
- Real-time occupancy tracking for high-altitude cantons and shelters.
- **$>90\%$ Capacity Diversion Trigger**:
  - When nearest shelter occupancy exceeds $90\%$, Dijkstra search automatically diverts evacuees to the next optimal shelter with remaining capacity (e.g. diverting from Harsil Army Cantonment at $91.6\%$ to Sukhi Ridge Shelter at $22\%$).

---

## 4. Telecom, Satellite Broadcast & Extreme-Crisis Communications

### A. C-DOT Cell Broadcast Engine (`backend/app/services/telecom/broadcast.py`)
- Formats 3GPP TS 23.041 compliant Cell Broadcast Center (CBC) geo-fenced emergency messages.
- Dispatches bilingual warnings (Hindi + English) to telecom base transceiver stations (BTS) covering threat polygons.

### B. ISRO NavIC (IRNSS) Satellite Downlink
- Encodes compressed 52-byte disaster alert packets with CRC-24 checksum for direct satellite downlink over ISRO NavIC L5/S-band.

### C. Satellite IoT Backhaul Failover
- Automated failover engine monitors fiber/4G heartbeat.
- When terrestrial lines are severed, failover engine seamlessly transitions data packets to BSNL Satellite IoT / Iridium SBD transceivers.

### D. Offline Bluetooth LE (BLE) Victim Finder
- Aggregates peer-to-peer BLE beacons emitted from citizen devices trapped under rubble or isolated without cell service, providing coordinates, accuracy, and trapped headcounts for NDRF teams.

---

## 5. Institutional Integration & Open Data Protocols

### A. Central Water Commission (CWC) & IMD Doppler Radar (`backend/app/services/institutional/cwc_imd.py`)
- Real-time connector to CWC hydrological stations on Bhagirathi (Harsil, Uttarkashi, Tehri), tracking Warning and Danger level exceedances.
- IMD Doppler Weather Radar connector applies Marshall-Palmer relation ($Z = 200 R^{1.6}$) to extract instantaneous rain rates and convective storm cells.

### B. Automated NDMA Post-Disaster Needs Assessment (PDNA) (`backend/app/services/institutional/pdna_generator.py`)
- Generates official NDMA-standard recovery dossiers across 5 core sectors:
  1. Housing & Settlements
  2. Transport, Roads & Culverts
  3. Agriculture & Apple Orchards
  4. Water Supply & Sanitation (WASH)
  5. Power & Telecom Grids
- Aggregates damages and losses in INR Crores and outputs prioritized early recovery action items.

### C. Community Disaster Resilience Index (CDRI) (`backend/app/services/institutional/resilience_index.py`)
- Computes composite resilience ratings ($0-100$) across 5 pillars: Physical Infrastructure, Social Vulnerability, Economic Coping Capacity, Institutional Readiness, and Hazard Exposure Penalty.

---

## 6. Breakthrough UI/UX & Operator Decision Support

### A. AI Incident Copilot (`frontend/src/components/copilot/CopilotDrawer.tsx`)
- Integrated into Command Center with live RAG over multi-source telemetry.
- Synthesizes real-time Situation Reports (SITREP) with one click.
- **Human-in-the-Loop Action Cards**: Proposes concrete tactical operations (Cell Broadcast, Shelter Diversion, SAR dispatch) with explicit Commander "Authorize & Execute" confirmation.

### B. NDMA PDNA Export Modal (`frontend/src/components/institutional/PDNAModal.tsx`)
- Allows disaster officers to select impacted settlements, assess damage matrices, and print/export official PDNA dossiers.

### C. 3D Mountain Terrain Perspective (`frontend/src/components/map/RiskMap.tsx`)
- Interactive 3D camera pitch/bearing controls allow operators to tilt the map view ($58^\circ$ pitch) and visualize steep Himalayan ridge profiles, river corridors, and evacuation routes.
