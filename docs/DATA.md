# Data Provenance & Specification Document

**Project**: Hilly-Region Flash Flood & Landslide Early Warning System (SIH 2026, PS 26192, MHA/NDRF)  
**Pilot District**: Uttarkashi, Uttarakhand

---

## 1. Real vs. Synthetic Data Classification

In accordance with project transparency guidelines, all data sources and modeling inputs are strictly demarcated below into **Real** and **Synthetic**:

### Real Elements
- **Village Names & Locations**: 
  - Real administrative settlements in Uttarkashi district:
    - *Bhagirathi Valley*: Harsil, Dharali, Mukhba, Jhala, Sukhi, Gangnani, Bhatwari, Maneri, Netala, Uttarkashi Town, Joshiyara, Matli, Dunda, Chinyalisaur, Singot, Athali.
    - *Yamuna & Kamal Valleys*: Barkot, Naugaon, Purola.
    - *Tons & Supa Valleys*: Mori, Netwar, Sankri, Taluka, Osla, Jakhol.
- **Geographic Coordinates**:
  - True geographic anchor latitudes (30.56°N to 31.14°N) and longitudes (78.04°E to 78.75°E) placing settlements in their genuine Himalayan river basins.
- **Elevation Hierarchy**:
  - Genuine macro-elevation hierarchy reflecting true relief, ranging from 850m (Chinyalisaur reservoir edge) to 2,745m (Harsil alpine valley).

---

### Synthetic Elements
- **Populations & Demographics**:
  - Synthetic estimates (350 to 4,800 residents per settlement) for evacuation load modeling.
- **Village Spatial Boundaries**:
  - Synthetic bounding box polygons (~600m across) representing settlement extents.
- **Sensors & Telemetry Network**:
  - Synthetic rain gauges, soil moisture sensors, and river gauging stations with generated device IDs and timestamps.
- **Relief Shelters & Evacuation Routes**:
  - Synthetic high-ground community refuges, walking duration metrics (10 to 28 mins), and path severance cut-risks.
- **5-Year Hourly Rainfall (2019-2023)**:
  - Generative physics-informed rainfall time series ($N = 1,095,600$ hourly records) with:
    - Calibrated monsoon seasonal envelope (June 15 to September 30 peak, centered on July 24).
    - Secondary winter Western Disturbances (December to February).
    - Diurnal afternoon convective cycle (14:00 to 18:00).
    - Injected cloudburst extremes exceeding **100+ mm in 3 hours** (intensities reaching 48 to 68 mm/hr).
- **Antecedent Soil Moisture**:
  - Physically simulated bucket model:
    $$\frac{dS}{dt} = P_t - ET_t - k_{\text{drain}} \cdot S_t$$
    with maximum capacity $S_{\max} = 100 \text{ mm}$ and drainage recession constant $k = 0.018 \text{ hr}^{-1}$.
- **Terrain Derivatives**:
  - Synthetic micro-topography calibrated to valley elevation:
    - *Slope*: 14° to 52° (steeper gorge walls at higher elevations like Harsil and Dharali).
    - *Aspect*: 0° to 360° compass orientation.
    - *Curvature*: -0.05 to +0.05 (concave hollows vs convex ridges).
    - *Upstream Catchment Area*: 4 to 160 $\text{km}^2$.
    - *Distance to Nearest Stream*: 10m to 450m.
    - *NDVI*: 0.18 to 0.82.
- **Landslide Inventory**:
  - 300 discrete synthetic slope failure events triggered by extreme rainfall pulses and high antecedent moisture on steep slopes ($\ge 22^\circ$), classified into *debris flows*, *shallow translational slides*, *rockfalls*, and *mudslides*.
- **Processed Feature Table**:
  - Multi-window rolling rainfall features (1h, 3h, 6h, 24h, 72h) with rare positive labels (`landslide_within_6h` rate: 0.1643% $\ll 1\%$).

---

## 2. Data Loaders Architecture & Fallback Behavior

All data loaders in [`ml/data/loaders.py`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/ml/data/loaders.py) follow an **offline-first graceful degradation pattern**:

```
                       Check Local File in /data/raw/
                                     │
                     ┌───────────────┴───────────────┐
                     ▼                               ▼
                 [Exists]                        [Missing]
                     │                               │
            Load Real Dataset             Run Synthetic Generator
         (GPM, SRTM, GSI Catalog)       (Physics Simulation & DB Anchor)
```

### Supported Loaders

| Function | Raw Local Target Path | Synthetic Fallback Mechanism |
| :--- | :--- | :--- |
| `load_rainfall` | `/data/raw/rainfall/*.parquet` or `*.csv` | `SyntheticDataGenerator.generate_5year_hourly_rainfall` |
| `load_dem` | `/data/raw/dem/*.parquet` or `*.csv` | `SyntheticDataGenerator.generate_terrain_features` |
| `load_soil_moisture`| `/data/raw/soil_moisture/*.csv` | Bucket-model antecedent saturation index |
| `load_land_use` | `/data/raw/land_use/*.csv` | Synthetic NDVI feature generator |
| `load_landslide_inventory` | `/data/raw/landslides/landslide_inventory.csv` | Physics-triggered ~300 event generator |
| `load_feature_table` | `/data/processed/feature_table.parquet` | Full end-to-end multi-window pipeline |

---

## 3. Storage Formats & Locations

- **Raw Landslide Catalog**: [`/data/raw/landslides/landslide_inventory.csv`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/data/raw/landslides/landslide_inventory.csv)
  - Columns: `village_id, lat, lon, date, type, rain_3h_at_failure, rain_24h_at_failure, soil_moisture_at_failure, slope_deg`
- **Processed Feature Store**: [`/data/processed/feature_table.parquet`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/data/processed/feature_table.parquet)
  - 1,095,600 rows $\times$ 16 columns.
  - Zero null/missing values.
  - Target label: `landslide_within_6h` (1 if failure occurs in $[t+1\text{h}, t+6\text{h}]$, 0 otherwise).

---

## 4. Live API & Three-Layer Connector Hierarchy

The real-time ingestion layer connects to external meteorology services while enforcing strict provenance:

1. **LIVE**: Direct call to Open-Meteo API (`https://api.open-meteo.com/v1/forecast`) with 5s timeout, exponential backoff (max 3 retries), and rate limit handling.
2. **CACHED**: Stored in Redis (or in-memory fallback) with a configurable **60-minute TTL**.
3. **SIMULATED**: Physics-guided synthetic generator reproducing monsoon seasonality and cloudburst dynamics.

> [!IMPORTANT]
> **Strict Provenance Rule**: Every returned telemetry and observation record carries a mandatory `data_source` field: `"LIVE"`, `"CACHED"`, or `"SIMULATED"`. The system never claims simulated data is live.

---

## 5. Case-Based Analog Event Library

Located at [`/data/processed/analog_library.json`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/data/processed/analog_library.json), the analog library provides case-based retrieval for operational explainability and situational awareness.

### 5.1 Historical Disaster Reconstructions
Built from public geological and meteorological survey reports (NDMA, GSI, IMD, Wadia Institute of Himalayan Geology).
- **Strict Provenance Label**: `"approximate reconstruction from public reports, not observed data"`.
- **Precaution**: Casualty counts and exact rainfall totals are deliberately not stated as verified measurements; all figures are denoted as approximate.

| Event ID | Event Name | Region | Date | Approximate Conditions | Outcome & Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `HIST_KEDARNATH_2013` | Kedarnath Cloudburst & Glacial Outburst | Rudraprayag, Uttarakhand | 2013-06-16 | ~325 mm / 24h, antecedent snowmelt saturation ($m \approx 0.92$), steep 36.5° moraine slopes | Catastrophic debris avalanche and Chorabari moraine breach; extensive settlement devastation (approximate public reports) |
| `HIST_CHAMOLI_2021` | Chamoli Ronti Peak Rock-Ice Avalanche | Chamoli, Uttarakhand | 2021-02-07 | Winter dry conditions (~5 mm rain), 44° steep north face, thermal crack detachment | Wedge detachment of ~27 million m³ rock/ice creating hyper-concentrated debris torrent destroying Tapovan hydro project |
| `HIST_WAYANAD_2024` | Wayanad Extreme Orographic Deluge | Wayanad, Kerala | 2024-07-30 | ~370 mm / 24h (~572 mm / 48h), near-saturated laterite regolith ($m \approx 0.95$), 31° slopes | Massive debris slide flattening Chooralmala and Mundakkai river terraces and tea estate quarters |
| `HIST_MANDI_2023` | Mandi Beas Valley Cloudburst Series | Mandi, Himachal Pradesh | 2023-08-14 | ~165 mm / 24h, antecedent monsoon saturation ($m \approx 0.86$), 34.5° highway cut batters | Widespread translational slides, cut-slope failures, and national highway blockages |

### 5.2 Simulator-Generated Synthetic Analogs
- **Count**: 48 diverse scenarios (52 events total in library).
- **Strict Provenance Label**: `"synthetic"`.
- **Composition**: 50% slope failure events and 50% non-failure heavy storm scenarios across varying hillslope gradients (16° to 48°), antecedent moisture (0.25 to 0.94), and rainfall hyetograph shapes.


