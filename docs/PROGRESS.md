# Project Progress Log: Hyper-Local FlashFlood Prediction

**Project**: Hyper-Local FlashFlood Prediction (SIH 2026, PS 26192, MHA/NDRF)  
**Pilot District**: Uttarkashi, Uttarakhand (Bhagirathi, Yamuna, Kamal, and Tons Valleys)

---

## Task 1: Monorepo Scaffold & Core Backend Setup (Completed)

### 1. What Was Done
- **Monorepo Directory Layout**: Created the standardized folder structure:
  - `/backend` (FastAPI app, core configuration, database models, Alembic migrations)
  - `/ml` (Simulation, conformal prediction, thresholds, evaluation)
  - `/frontend` (Vite + React + MapLibre GL)
  - `/data` (Local SQLite database storage, synthetic terrain and catalog data)
  - `/docs` (Architecture and progress documentation)
  - `/tests` (Unit and integration test suites)
  - `/scripts` (Database seeding and operational utility scripts)
- **Containerization (`docker-compose.yml`)**:
  - `postgres`: PostGIS image (`postgis/postgis:15-3.3-alpine`) with automated health checks.
  - `redis`: Redis 7 alpine (`redis:7-alpine`) with health checks.
  - `backend`: Multi-stage Python 3.11 container mounting local source code with live reload.
  - `frontend`: Vite React build container on port 5173.
- **Dual-Mode Database Architecture (SQLite Default + PostGIS Engine)**:
  - Defaulting to SQLite (`sqlite:///./data/ews.db`) for zero-configuration, fully offline execution without requiring active Docker daemons or spatialite libraries.
  - Stores geometry as GeoJSON/WKT strings in SQLite mode with Shapely parsing; switches dynamically to GeoAlchemy2 `Geometry` columns when `DATABASE_URL` targets PostgreSQL.
- **Database Schema (9 Core Tables Implemented)**:
  1. `villages`: `id`, `name`, `district`, `geometry`, `population`, `lat`, `lon`, `elevation`.
  2. `sensors`: `id`, `village_id`, `type`, `status`, `last_seen`.
  3. `observations`: `id`, `time`, `sensor_id`, `variable`, `value`.
  4. `risk_assessments`: `id`, `time`, `village_id`, `probability`, `lower`, `upper`, `tier`, `explanation_json`.
  5. `alerts`: `id`, `village_id`, `tier`, `message` (strictly max 160 characters), `created_at`.
  6. `alert_deliveries`: `id`, `alert_id`, `recipient_id`, `channel`, `status`, `sent_at`, `acked_at`.
  7. `recipients`: `id`, `village_id`, `phone`, `language`, `vulnerable_flag`, `volunteer_id`.
  8. `shelters`: `id`, `name`, `geometry`, `capacity`, `village_id`.
  9. `routes`: `id`, `from_village`, `to_shelter`, `length_m`, `est_walk_minutes`, `cut_risk`.
- **Alembic Migrations**:
  - Initialized Alembic configuration and migration `001_initial_schema.py`.
  - Verified full migration upgrade and downgrade cycles.
- **Pilot District Seed Script (`scripts/seed_data.py`)**:
  - Generated 25 realistic pilot villages in Uttarkashi district (Harsil, Dharali, Mukhba, Jhala, Sukhi, Gangnani, Bhatwari, Maneri, Netala, Uttarkashi Town, Joshiyara, Matli, Dunda, Chinyalisaur, Barkot, Naugaon, Purola, Mori, Netwar, Sankri, Taluka, Osla, Jakhol, Singot, Athali).
  - Realistic elevation range: 850m to 2,745m.
  - Seeded associated rainfall gauges, soil moisture sensors, river gauges, designated high-ground shelters, evacuation routes with walking times and cut risks, and volunteer/vulnerable recipient registries.
- **Cross-Platform Automation**:
  - `Makefile`: `make up`, `make down`, `make test`, `make seed`.
  - Windows PowerShell runners: `scripts/run.ps1` (`up`, `down`, `test`, `seed`), `scripts/up.ps1`, `scripts/down.ps1`, `scripts/test.ps1`, `scripts/seed.ps1`.
- **FastAPI Endpoints**:
  - `GET /health`: Returns service health, database connection status, redis status, and database engine type.
  - `GET /`: Returns operational status and API documentation links.

---

### 2. How to Run and Test

#### Automated Test Suite
Run unit tests across database tables, seed entities, and API health:
```bash
# On Linux / macOS:
make test

# On Windows PowerShell:
./scripts/run.ps1 test
# or:
python -m pytest tests/ -v
```

#### Seeding the Pilot District
Populate the database with the 25 Uttarkashi pilot villages:
```bash
# On Linux / macOS:
make seed

# On Windows PowerShell:
./scripts/run.ps1 seed
# or:
python scripts/seed_data.py
```

#### Running the Backend
```bash
# Start FastAPI backend locally:
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Test health check endpoint in a separate terminal:
python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/health').json())"
```

#### Running via Docker Compose (when Docker is available)
```bash
# On Linux / macOS / Docker Desktop:
make up

# Check logs:
docker compose logs -f backend
```

---

### 3. Verification Results
- **pytest tests**: 5 passed in 2.95s (`test_database_tables_exist`, `test_seed_villages_count_and_properties`, `test_seed_sensors_and_shelters`, `test_fastapi_health_endpoint`, `test_fastapi_root_endpoint`).
- **HTTP GET `/health` verified**:
  ```json
  {
    "status": "ok",
    "database": "connected",
    "redis": "offline_fallback",
    "database_type": "sqlite",
    "version": "0.1.0",
    "environment": "development"
  }
  ```
- **Alembic migration test**: Fully applied and reversible.

---

## Task 2: ML Data Module & Synthetic Generation Pipeline (Completed)

### 1. What Was Done
- **Data Loaders (`/ml/data/loaders.py`)**:
  - Implemented offline-first loaders for:
    - `load_rainfall`: Checks `/data/raw/rainfall/` for real GPM IMERG / IMD gridded files; falls back to synthetic generator if missing.
    - `load_dem`: Checks `/data/raw/dem/` for SRTM GeoTIFF/CSV; falls back to elevation-calibrated synthetic terrain generator.
    - `load_soil_moisture`: Checks `/data/raw/soil_moisture/`; falls back to physical bucket model.
    - `load_land_use`: Checks `/data/raw/land_use/`; falls back to synthetic NDVI.
    - `load_landslide_inventory`: Checks `/data/raw/landslides/landslide_inventory.csv`; falls back to synthetic catalog.
    - `load_feature_table`: Loads `/data/processed/feature_table.parquet`; dynamically runs pipeline if missing.
- **Physics-Informed Synthetic Generator (`/ml/data/synthetic.py`)**:
  - Anchors directly to the 25 Uttarkashi villages in the database (never invents new villages).
  - Generates 5 years of hourly rainfall (2019–2023, 43,824 hours per village = 1,095,600 total observations).
  - Modeled realistic monsoon seasonality with peak in July–August and secondary winter Western Disturbances.
  - Injected convective cloudburst pulses exceeding **100+ mm in 3 hours**.
  - Implemented physical bucket model for antecedent soil moisture accounting for precipitation, diurnal evapotranspiration, and drainage recession.
  - Derived terrain features per village: `slope` (14°–52°), `aspect` (0°–360°), `curvature`, `elevation` (from DB), `upstream_catchment_area` (4–160 $\text{km}^2$), `distance_to_stream` (10m–450m), and `ndvi`.
- **Synthetic Landslide Inventory**:
  - Created 300 discrete slope failure events strictly consistent with rainfall extremes and steep slopes ($\ge 22^\circ$).
  - Classified by failure mechanism: `debris_flow`, `shallow_translational`, `rockfall`, `mudslide`.
  - Persisted to [`/data/raw/landslides/landslide_inventory.csv`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/data/raw/landslides/landslide_inventory.csv).
- **Multi-Window Feature Store**:
  - Computed rolling cumulative rainfall windows: `rain_1h`, `rain_3h`, `rain_6h`, `rain_24h`, `rain_72h`.
  - Target label: `landslide_within_6h` (1 if failure occurs within $[t+1\text{h}, t+6\text{h}]$, 0 otherwise).
  - Positive label frequency: **0.1643%** (strictly rare and well under 1%).
  - Zero null/NaN values across all 1,095,600 rows.
  - Persisted to [`/data/processed/feature_table.parquet`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/data/processed/feature_table.parquet).
- **Documentation (`/docs/DATA.md`)**:
  - Comprehensive document explicitly categorizing real geographic anchors vs synthetic demographic/physics-simulated elements.
- **Unit Tests (`tests/test_ml_data.py`)**:
  - 6 unit tests validating DB village anchoring, terrain plausibility, monsoon seasonality, cloudburst extremes, inventory schema, rare target rate, and loader fallbacks.

---

### 2. How to Run and Test

#### Run the Synthetic Data Pipeline
```bash
python -m ml.data.synthetic
```

#### Run All Unit Tests
```bash
python -m pytest tests/ -v
```

---

### 3. Verification Results
- **Full Test Suite**: **11/11 tests passed** in 12.67s.
  - `tests/test_ml_data.py`: 6 passed.
  - `tests/test_scaffold.py`: 5 passed.
- **Data Artifacts Verified**:
  - `data/raw/landslides/landslide_inventory.csv`: 300 events.
  - `data/processed/feature_table.parquet`: 1,095,600 rows $\times$ 16 columns, positive label rate: 0.1643%.

---

## Task 3: Real-Data & API Connector Layer (Completed)

### 1. What Was Done
- **Live Open-Meteo Connector (`/ml/data/connectors/weather.py`)**:
  - Direct connection to the Open-Meteo public API (no API key required).
  - Fetches hourly precipitation forecast, past 7 days precipitation, and soil moisture (`soil_moisture_0_to_1cm`) for each village using exact lat/lon coordinates.
  - Configured with 5.0s timeouts, bounded exponential backoff (max 3 retries), and rate limit handling (HTTP 429 backoff).
  - Synchronous and asynchronous batch query methods with concurrency bounding.
- **Three-Layer Data Source Manager (`/backend/app/services/ingestion/manager.py`)**:
  - Enforces strict hierarchy: **LIVE** $\longrightarrow$ **CACHED** $\longrightarrow$ **SIMULATED**.
  - Cache Layer (`/backend/app/services/ingestion/cache.py`): Primary Redis with in-memory TTL fallback (60 minutes).
  - Strict provenance tagging: Every record returned carries `data_source` as `"LIVE"`, `"CACHED"`, or `"SIMULATED"`. Never claims simulated data is live.
- **Background Telemetry Ingestion Scheduler (`/backend/app/services/ingestion/scheduler.py`)**:
  - Background worker running every 30 minutes refreshing village weather and persisting new rows to the `observations` database table (`time`, `sensor_id`, `variable`, `value`).
  - Completely non-blocking using `asyncio.to_thread`.
- **FastAPI Lifespan Startup Preloading (`/backend/app/main.py`)**:
  - Preloads the pre-computed processed feature table parquet once into memory (`app.state.feature_table`) at server startup.
  - Eliminates slow file reads inside API request handlers.
  - Logs exact load times (e.g. 1.09M rows in ~0.5s).
  - Spawns background ingestion task on startup and cleanly cancels on shutdown.
- **Data Status Endpoint (`GET /api/v1/data/status`)**:
  - Returns operational state (`LIVE`/`CACHED`/`SIMULATED`), last successful fetch timestamp, and latency per source.
  - Manual ingestion trigger via `POST /api/v1/data/refresh`.
- **District Clipping Script (`/scripts/clip_to_district.py`)**:
  - Clips raw external rasters (GeoTIFF/NetCDF) and vector/tabular catalogs to the Uttarkashi district bounding box (`[77.85°E, 30.45°N, 79.15°E, 31.45°N]`).
- **External Data Guide (`/docs/DATA_SOURCES.md`)**:
  - Comprehensive guide with procurement instructions for SRTM DEM, GSI Bhukosh landslide inventory, IMD gridded rainfall, GPM IMERG via NASA Earthdata, and Sentinel-1/2 SAR/Optical imagery.
- **Unit Tests (`tests/test_connectors.py`)**:
  - 7 unit tests verifying connector success, timeouts, malformed responses, HTTP 429 rate limiting, 3-layer fallback transitions, status endpoint, and background DB writes.

---

### 2. How to Run and Test

#### Run Connector & Ingestion Unit Tests
```bash
python -m pytest tests/test_connectors.py -v
```

#### Run Full Test Suite
```bash
python -m pytest tests/ -v
```

#### Test Data Status Endpoint
```bash
# Start backend server:
python -m uvicorn backend.app.main:app --port 8000

# Query data status in separate terminal:
python -c "import httpx; print(httpx.get('http://127.0.0.1:8000/api/v1/data/status').json())"
```

#### Clip an External Raster to Uttarkashi BBOX
```bash
python scripts/clip_to_district.py --input /path/to/raster.tif --output data/raw/dem/srtm_uttarkashi.tif
```

---

### 3. Verification Results
- **Full Test Suite**: **18/18 tests passed** in 17.03s:
  - `tests/test_connectors.py`: 7 passed.
  - `tests/test_ml_data.py`: 6 passed.
  - `tests/test_scaffold.py`: 5 passed.
- **Data Provenance**: Confirmed zero false claims of live data; fallback hierarchy verified across all scenarios.

---

## Task 4: Geotechnical Physics & Catchment Hydrology Simulation (Completed)

### 1. What Was Done
- **Infinite-Slope Limit-Equilibrium Model (`/ml/physics/slope_stability.py`)**:
  - Implemented the vectorized infinite-slope factor-of-safety model:
    $$FS = \frac{c' + (\gamma \cdot z - m \cdot \gamma_w \cdot z) \cos^2(\theta) \tan(\phi')}{\gamma \cdot z \sin(\theta) \cos(\theta)}$$
  - Driven by rainfall infiltration and antecedent moisture:
    $$m = \text{clip}\left(m_0 + \frac{P_{\text{cum}}}{z \cdot \eta \cdot 1000}, 0.0, 1.0\right)$$
  - Full NumPy vectorization supporting arbitrary array shapes and multidimensional evaluations.
- **Monte Carlo Geotechnical Scenario Generator (`/ml/physics/scenario_generator.py`)**:
  - Generates realistic combinations of hillslope gradient (12° to 54°), soil cohesion (2.5 to 30.0 kPa), internal friction angle (20° to 44°), regolith depth (0.6 to 3.8m), rainfall events (0 to 260 mm), and antecedent saturation (0.12 to 0.88).
  - Injected geotechnical parameter uncertainty and spatial heterogeneity noise ($\sigma = 0.08$) simulating natural variations in root reinforcement and localized pore-pressure spikes.
  - Labeled each scenario as failed ($FS < 1.0$) or stable ($FS \ge 1.0$).
  - Generated and saved **120,000 synthetic scenarios** (failure rate: **13.68%**) to [`/data/processed/physics_synthetic.parquet`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/data/processed/physics_synthetic.parquet) with zero NaNs.
- **Operational Explainability Function (`factor_of_safety`)**:
  - Accepts village features (slope, elevation, antecedent moisture) and rainfall time series/accumulations.
  - Returns deterministic FS, dynamic saturation index, driving vs. resisting shear stresses (kPa), and operational stability diagnosis (`STABLE`, `MARGINAL`, `CRITICAL_FAILURE`).
- **Catchment Hydrology & Runoff Module (`/ml/physics/hydrology.py`)**:
  - SCS Curve Number excess runoff formulation:
    $$Q_{\text{cum}} = \frac{(P - I_a)^2}{P - I_a + S} \quad (P > I_a)$$
  - SCS lag and time of concentration calculation $T_c$ calibrated for steep mountain watersheds.
  - Unit hydrograph convolution yielding river discharge hydrograph and catchment peak discharge ($Q_{\text{peak}}$ in $\text{m}^3/\text{s}$).
  - Enforced strict conservation of mass ($V_{\text{runoff}} + V_{\text{retention}} \equiv V_{\text{precip}}$ with volumetric error $< 0.001\%$).
- **Response Curve Visualization**:
  - Generated publication-grade plot [`/docs/fs_vs_rainfall.png`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/fs_vs_rainfall.png) comparing slope stability degradation across 3 slope regimes: gentle (20°), moderate (32°), and steep (44°).
  - Created interactive Jupyter notebook [`/notebooks/fs_vs_rainfall.ipynb`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/notebooks/fs_vs_rainfall.ipynb) with full LaTeX geotechnical derivations and interactive visualizations.
- **Unit Tests (`tests/test_physics.py`)**:
  - 6 unit tests verifying monotonic FS decrease with slope, monotonic FS decrease with saturation, explainability output schema, 120,000-row scenario dataset integrity, and strict SCS-CN runoff mass balance.

---

### 2. How to Run and Test

#### Run Physics Scenario Generator (>= 100,000 Scenarios)
```bash
python -m ml.physics.scenario_generator
```

#### Generate FS vs. Rainfall Response Plot
```bash
python ml/physics/plot_fs_curves.py
```

#### Run Physics Unit Tests
```bash
python -m pytest tests/test_physics.py -v
```

#### Run Full Test Suite Across All Modules
```bash
python -m pytest tests/ -v
```

---

### 3. Verification Results
- **Full Test Suite**: **24/24 tests passed** in 17.63s:
  - `tests/test_physics.py`: 6 passed.
  - `tests/test_connectors.py`: 7 passed.
  - `tests/test_ml_data.py`: 6 passed.
  - `tests/test_scaffold.py`: 5 passed.
- **Physics Dataset**: `data/processed/physics_synthetic.parquet` (120,000 rows $\times$ 10 columns, zero NaNs, 13.68% failure rate).
- **Figure & Notebook**: `docs/fs_vs_rainfall.png` and `notebooks/fs_vs_rainfall.ipynb` verified.

---

## Task 5: Base Model Training, Physics Transfer & Dual Holdout Verification (Completed)

### 1. What Was Done
- **Physics Pretrained Landslide Risk Model (`ml/models/base_model.py`)**:
  - Implemented `LandslideRiskModel` using `xgboost.XGBClassifier` with hyperparameters calibrated for high-dimensional, extreme-imbalance tabular geotechnical data (`n_estimators=150`, `max_depth=5`, `learning_rate=0.06`).
  - Pretrained on the 120,000 synthetic physics failure scenarios (`data/processed/physics_synthetic.parquet`).
  - Fine-tuned on the 1,095,600 village spatio-temporal feature records (`data/processed/feature_table.parquet`), dynamically integrating `factor_of_safety` as a core mechanistic input feature.
  - Implemented dynamic class reweighting via `scale_pos_weight` tailored to the 0.16% rare-event label proportion.
  - Persisted model artifact to [`ml/models/saved/landslide_xgboost.joblib`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/ml/models/saved/landslide_xgboost.joblib) with full serialization and loading routines.
  - Functional `predict(features)` interface accepting raw dictionary or Pandas DataFrame and returning calibrated failure probability.
- **Rainfall Intensity-Duration (I-D) Threshold Baseline (`ml/models/baseline.py`)**:
  - Implemented `RainfallThresholdBaseline` representing empirical Caine/GSI Himalayan warning guidelines.
  - Formulates alarm condition based on 3-hour storm burst ($R_{3h} \ge \tau_{3}$) or 24-hour cumulative precipitation on steep terrain ($R_{24h} \ge \tau_{24} \land \theta \ge \theta_{crit}$).
  - Self-calibrates threshold parameters on training folds using grid search to optimize Critical Success Index (CSI).
- **Strict Spatial + Temporal Cross-Validation (`ml/evaluate.py`)**:
  - Strictly prevents spatial and temporal data leakage:
    - **Spatial Holdout**: 5 whole villages (20% of settlements: `VIL_UTK_21` to `VIL_UTK_25`) never seen during training.
    - **Temporal Holdout**: Calendar year 2023 held out (model trained solely on 2019–2022).
    - **Split**: 701,280 train rows vs. 43,800 test rows (90 positive hours).
  - Evaluates both models on non-accuracy metrics: POD (Recall), FAR, CSI (Threat Score), ROC-AUC, PR-AUC, Brier Score, and Actionable Lead Time (hours prior to failure).
  - Generated comprehensive documentation in [`docs/RESULTS.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/RESULTS.md) and machine-readable [`docs/evaluation_results.json`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/evaluation_results.json).
  - Explicitly labeled all evaluations as conducted on synthetic data with honest discussion of baseline vs. ML trade-offs.
- **End-to-End Reproducible Pipeline (`python -m ml.train`)**:
  - Orchestrates pretraining, fine-tuning, serialization, and dual holdout evaluation in a single command.
  - Executes in **11.2 seconds** (well under the 5-minute requirement).
- **Unit & Integration Test Suite (`tests/test_models.py`)**:
  - 5 tests verifying pretraining, fine-tuning, inference probability bounds ($[0, 1]$), persistence round-trip, functional API, spatial/temporal disjointness, and exact metric formulations.

---

### 2. How to Run and Test

#### Run the End-to-End Training & Evaluation Pipeline
```bash
python -m ml.train
```

#### Run Model Unit Tests
```bash
python -m pytest tests/test_models.py -v
```

#### Run Full Test Suite Across All Modules
```bash
python -m pytest tests/ -v
```

---

### 3. Verification Results
- **Full Test Suite**: **29/29 tests passed** in 18.17s:
  - `tests/test_models.py`: 5 passed.
  - `tests/test_physics.py`: 6 passed.
  - `tests/test_connectors.py`: 7 passed.
  - `tests/test_ml_data.py`: 6 passed.
  - `tests/test_scaffold.py`: 5 passed.
- **Model Evaluation Highlights (Spatial + Temporal Holdout)**:
  - **XGBoost ROC-AUC**: 0.9460 vs. Baseline 0.9225 (+0.0235)
  - **XGBoost PR-AUC**: 0.1459 vs. Baseline 0.0700 (+0.0759)
  - **XGBoost CSI**: 0.0733 vs. Baseline 0.0344 (+0.0389)
  - **XGBoost Brier Score**: 0.0127 vs. Baseline 0.0244 (-0.0117, lower is better)
  - **Average Lead Time**: 3.67 hours vs. Baseline 3.47 hours (+0.20 hours)
- **Artifacts Created**:
  - [`ml/models/saved/landslide_xgboost.joblib`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/ml/models/saved/landslide_xgboost.joblib)
  - [`docs/RESULTS.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/RESULTS.md)
  - [`docs/evaluation_results.json`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/evaluation_results.json)

---

## Task 6: Probability Calibration & Matched Operating Points Verification (Completed)

### 1. What Was Done
- **Post-Hoc Probability Calibration (`ml/models/base_model.py`)**:
  - Identified that raw XGBoost outputs were inflated due to class reweighting (`scale_pos_weight`).
  - Added dedicated probability calibrators:
    - `IsotonicCalibrator`: Non-parametric piecewise constant isotonic regression.
    - `PlattCalibrator`: Sigmoid logistic regression fitted on model log-odds.
  - Structured time-ordered validation split:
    - **Train split**: 2019–2021 (526,080 rows across 20 training settlements).
    - **Calibration split**: 2022 (175,200 rows across 20 training settlements).
    - **Test split**: 2023 (43,800 rows across 5 held-out settlements).
  - Evaluated validation Brier score on the 2022 fold:
    - Uncalibrated Brier: `0.011144`
    - Isotonic Regression Brier: `0.001456`
    - Platt Scaling Brier: `0.001472`
    - Dynamically selected **Isotonic Regression** for superior probability calibration.
  - Updated `predict_proba(X)` and `predict(features)` to output strictly calibrated probabilities bounded in $[0.0, 1.0]$.
  - Persisted calibrator artifact within [`ml/models/saved/landslide_xgboost.joblib`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/ml/models/saved/landslide_xgboost.joblib).
- **Expected Calibration Error (ECE) & Reliability Diagrams (`ml/evaluate.py`)**:
  - Evaluated on holdout test set (2023 unseen storms across 5 unseen villages):
    - Raw XGBoost ECE: **0.031102 (3.11%)**
    - Calibrated XGBoost ECE: **0.000440 (0.044%)** — **70.7x reduction in calibration error**.
  - Generated publication-grade reliability diagram: [`docs/calibration_curve.png`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/calibration_curve.png).
- **Brier Skill Score (BSS) Against Climatology**:
  - Climatology reference baseline: constant probability equal to training set prevalence ($p = 0.001597$, Brier score = 0.002051).
  - Calibrated model test Brier score: **0.001901**.
  - Brier Skill Score: **+0.0730 (+7.30%)** — confirms genuine probabilistic skill over climatology.
- **Fair Comparison at Matched Operating Points**:
  - Eliminated arbitrary threshold comparisons; evaluated model vs baseline at matched operating points:
    - **Matched POD (Recall ≈ 56.67%)**: Calibrated XGBoost achieved FAR = **95.67%** (vs Baseline 96.47%, $\Delta = -0.80\%$) and CSI = **0.0418** (vs Baseline 0.0344, $\Delta = +0.0074$).
    - **Matched FAR (False Alarm ≈ 96.47%)**: Calibrated XGBoost achieved POD = **54.44%** (vs Baseline 56.67%, $\Delta = -2.22\%$) and CSI = **0.0418** (vs Baseline 0.0344, $\Delta = +0.0074$).
  - Generated Precision-Recall curve: [`docs/precision_recall_curve.png`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/precision_recall_curve.png).
- **Terminology Sanitization**:
  - Removed premature "calibrated" claims across docstrings and comments in `base_model.py`, `baseline.py`, and `models.py`.
  - Preserved synthetic data disclosures in [`docs/RESULTS.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/RESULTS.md).
- **Unit & Integration Test Suite (`tests/test_models.py`)**:
  - Added tests for calibration selection (Isotonic vs Platt), ECE reduction, Brier Skill Score formulation, and matched operating points sweep.

---

### 2. How to Run and Test

#### Run the End-to-End Training & Calibration Pipeline
```bash
python -m ml.train
```

#### Run Model Unit Tests
```bash
python -m pytest tests/test_models.py -v
```

#### Run Full Test Suite Across All Modules
```bash
python -m pytest tests/ -v
```

---

### 3. Verification Results
- **Full Test Suite**: **31/31 tests passed** in 18.80s:
  - `tests/test_models.py`: 7 passed.
  - `tests/test_physics.py`: 6 passed.
  - `tests/test_connectors.py`: 7 passed.
  - `tests/test_ml_data.py`: 6 passed.
  - `tests/test_scaffold.py`: 5 passed.
- **Calibration & Metrics Summary**:
  - **Selected Calibrator**: Isotonic Regression (validation Brier: 0.001456 vs Platt 0.001472)
  - **ECE**: 0.000440 (Calibrated) vs 0.031102 (Raw) — 70.7x reduction
  - **Brier Skill Score**: **+0.0730** (Positive skill over climatology)
  - **CSI at Matched POD**: **0.0418** (Model) vs 0.0344 (Baseline)
  - **ROC-AUC**: **0.9469** (Model) vs 0.9225 (Baseline)
  - **PR-AUC**: **0.1328** (Model) vs 0.0700 (Baseline)
- **Artifacts Created / Updated**:
  - Model: [`ml/models/saved/landslide_xgboost.joblib`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/ml/models/saved/landslide_xgboost.joblib)
  - Evaluation Report: [`docs/RESULTS.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/RESULTS.md)
  - Metrics JSON: [`docs/evaluation_results.json`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/evaluation_results.json)
  - Reliability Diagram: [`docs/calibration_curve.png`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/calibration_curve.png)
  - Precision-Recall Curve: [`docs/precision_recall_curve.png`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/precision_recall_curve.png)

---

## Task 7: Case-Based Analog Retrieval & Explainability Module (Completed)

### 1. What Was Done
- **Historical Reconstructions & Synthetic Analog Library (`ml/analog/library.py`)**:
  - Built 52-event analog case catalog ([`data/processed/analog_library.json`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/data/processed/analog_library.json)):
    - **4 Historical Disaster Reconstructions**: Kedarnath (2013), Chamoli (2021), Wayanad (2024), and Mandi (2023) built from NDMA, GSI, and IMD public survey reports.
    - **Strict Provenance Label**: Explicitly designated as `"approximate reconstruction from public reports, not observed data"`.
    - **Data Precaution**: Casualty numbers and exact rainfall amounts are strictly marked as approximate; never presented as verified operational measurements.
    - **48 Simulator-Generated Synthetic Analogs**: 50% landslide failure and 50% non-failure severe storm scenarios labeled `"synthetic"`.
- **Dual Representation Embedders (`ml/analog/embeddings.py`)**:
  - **Handcrafted Normalized Embedder**: 16-D feature vector summarizing 72h rainfall curve (peaks, centroid, burst ratio), antecedent saturation, hillslope gradient, relief, aspect, curvature, catchment area, and limit-equilibrium factor of safety.
  - **PyTorch Autoencoder Embedder**: Feedforward neural network (`80 -> 48 -> 28 -> 16 -> 28 -> 48 -> 80`) trained via MSE reconstruction loss.
  - **Representation Comparison**: `compare_embedding_methods()` verified autoencoder reconstruction convergence (MSE: 0.006) and semantic alignment with handcrafted features ($r \approx 0.52$).
- **Vector Index Engine (`ml/analog/index.py`)**:
  - `AnalogIndex` utilizing FAISS (`faiss.IndexFlatIP`) for cosine nearest-neighbor search with seamless fallback to pure NumPy matrix cosine search.
- **Explainability & DTW Retrieval (`ml/analog/matcher.py`)**:
  - `find_analogs(current_state, k=3)`: Returns top-3 matching events with similarity %, date, location, outcome, damage description, and natural-language causal reasoning.
  - **DTW Hyetograph Matching**: Implemented dynamic time warping (`compute_dtw_distance`) directly aligning 72-hour rainfall hyetograph temporal profiles.
  - **Key Driver Attribution**: Identifies primary physical hazard drivers (e.g. Factor of Safety breaches, 3h storm bursts, antecedent saturation surges).
  - **Explainability API**: `build_explanation_json(current_state)` formatted as `{"top_analogs": [...], "key_drivers": [...]}`.
- **Learned Probability Blending (`ml/analog/blend.py`)**:
  - Trained convex blend on the 2022 calibration split ($P_{\text{blend}} = \alpha \cdot P_{\text{base}} + (1 - \alpha) \cdot P_{\text{analog}}$).
  - Evaluated out-of-sample on the 2023 holdout test split:
    - Base Model BSS: **+0.0730**
    - Blended Model BSS: **+0.0730** (negligible difference $\Delta \text{BSS} < 0.0001$)
    - Optimal blend weight: $\alpha = 99.98\%$ for base model.
    - **Honest Finding**: Reported honestly that the analog engine serves primarily as a qualitative decision-support and transparent explainability tool for incident commanders rather than a statistical replacement for the calibrated base model.
- **Testing & Documentation**:
  - Added unit test suite [`tests/test_analog.py`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/tests/test_analog.py) (7 tests).
  - Updated [`docs/DATA.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/DATA.md) and [`docs/RESULTS.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/RESULTS.md).

---

### 2. How to Run and Test

#### Run Analog Unit Tests
```bash
python -m pytest tests/test_analog.py -v
```

#### Run Full Test Suite Across All Modules
```bash
python -m pytest tests/ -v
```

#### Run Full Training & Evaluation Pipeline
```bash
python -m ml.train
```

---

### 3. Verification Results
- **Full Test Suite**: **38/38 tests passed** in 22.81s:
  - `tests/test_analog.py`: 7 passed.
  - `tests/test_models.py`: 7 passed.
  - `tests/test_physics.py`: 6 passed.
  - `tests/test_connectors.py`: 7 passed.
  - `tests/test_ml_data.py`: 6 passed.
  - `tests/test_scaffold.py`: 5 passed.
- **Analog Retrieval Diagnostics**:
  - Library Size: 52 events (4 historical disaster reconstructions + 48 synthetic scenarios).
  - Autoencoder Latent Dim: 16 (MSE: 0.0060).
  - Learned Blend Weight: $\alpha = 0.9998$ base model, $0.02\%$ analog outcome.
  - Test Set BSS: +0.0730 (calibrated base model) vs +0.0730 (blended model).

---

## Task 8: Rare-Event Conformal Uncertainty & Decision Tiers (Completed)

### 1. What Was Done
- **Venn-Abers Conformal Uncertainty Predictor (`ml/uncertainty/conformal.py`)**:
  - Implemented multi-probabilistic Venn-Abers predictor addressing rare-event failure estimation (~0.16% base rate) on top of the isotonic-calibrated XGBoost model.
  - Fitted strictly on the time-ordered 2022 calibration split (175,200 records across 20 training settlements). Kept train (2019–2021) and test (2023 unseen storms + 5 held-out villages) untouched.
  - Generates non-parametric probability interval $[P_{\text{lower}}, P_{\text{upper}}]$ satisfying invariant $0.0 \le P_{\text{lower}} \le P_{\text{prob}} \le P_{\text{upper}} \le 1.0$.
  - Saved fitted calibrator artifact to [`ml/uncertainty/saved/venn_abers_calibrator.joblib`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/ml/uncertainty/saved/venn_abers_calibrator.joblib).
- **Conservative Decision Escalation Matrix (`docs/DECISION.md`)**:
  - Derived operational percentiles from calibration split:
    - **WATCH**: Top 2.0% ($P \ge 0.014637$)
    - **WARNING**: Top 0.5% ($P \ge 0.018041$)
    - **EVACUATE**: Top 0.1% ($P_{\text{lower}} \ge 0.150943$)
  - Enforced **Conformal Lower-Bound Gating**: Escalate to EVACUATE *only* if $P_{\text{lower}} \ge P_{\text{evacuate}}$; WARNING if $P \ge P_{\text{warning}}$; WATCH if $P \ge P_{\text{watch}}$; else NONE.
  - Conformal lower-bound gating cuts False Alarm Ratio down from 93.71% (at WATCH) to 59.09% (at EVACUATE), raising CSI to 0.1552.
- **Unified Risk Assessment API (`assess()`)**:
  - `assess(features) -> {probability, lower, upper, tier, tier_thresholds, explanation_json}`.
  - Integrates case-based analog engine for qualitative reasoning while strictly isolating analog landslide rate from the calibrated event probability.
- **Out-of-Sample Honest Verification & Coverage Report (`docs/RESULTS.md`)**:
  - Class-conditional coverage:
    - Negative class ($y=0$): **91.04%** (exceeds nominal 90% target).
    - Positive class ($y=1$): **81.11%** (honestly reported below 90% target due to extreme unseen cloudburst spikes).
  - Mean interval width: **0.000193** (extremely sharp in low-risk baseline).
  - Annual alert burden on test set:
    - EVACUATE: **8.8 alerts / village / year** (44 total alert hours across 5 villages).
    - WARNING: **65.8 alerts / village / year** (329 total alert hours).
    - WATCH: **127.2 alerts / village / year** (636 total alert hours).
- **Diagnostic Plot (`docs/conformal_coverage.png`)**:
  - 4-panel diagnostic plot covering interval bounds vs probability, binned empirical frequency coverage, class-conditional coverage bars, and decision tier operational trade-offs.
- **Unit Test Suite (`tests/test_uncertainty.py`)**:
  - Added 6 comprehensive unit tests validating interval bounds, monotonic threshold ordering, escalation logic, assess schema, and artifact serialization.

---

### 2. How to Run and Test

#### Run Uncertainty Unit Tests
```bash
python -m pytest tests/test_uncertainty.py -v
```

#### Run Full Test Suite Across All Modules
```bash
python -m pytest tests/ -v
```

---

### 3. Verification Results
- **Full Test Suite**: **44/44 tests passed** in ~28s:
  - `tests/test_uncertainty.py`: 6 passed.
  - `tests/test_analog.py`: 7 passed.
  - `tests/test_models.py`: 7 passed.
  - `tests/test_physics.py`: 6 passed.
  - `tests/test_connectors.py`: 7 passed.
  - `tests/test_ml_data.py`: 6 passed.
  - `tests/test_scaffold.py`: 5 passed.

---

## Task 9: Per-Village Bayes-Optimal Thresholds & Episode Evaluation (Completed)

### 1. What Was Done
- **Relative Societal Cost Modeling (`ml/decision/thresholds.py`)**:
  - Implemented `compute_village_costs()` defining $C_{\text{miss}}$ and $C_{\text{false\_alarm}}$ as relative non-monetary units based on exposed population, vulnerable residents (2.5x weight), hillslope gradient ($>25^\circ$), stream channel proximity ($<100\text{m}$), historical fatigue, and evacuation disruption.
  - Documented explicit assumptions in [`docs/DECISION.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/DECISION.md).
- **Bayes-Optimal Threshold Engine (`compute_bayes_optimal_threshold`)**:
  - Solves $p^* = C_{\text{false\_alarm}} / (C_{\text{false\_alarm}} + C_{\text{miss}})$.
  - Added operational clipping bounds $[0.005, 0.250]$ and maximum annual alert burden constraint per village.
- **Episode-Level Evaluation (`evaluate_episode_level`)**:
  - Merges consecutive alert hours (gap $\le 6\text{h}$) into coordinated emergency episodes.
  - Evaluated on 2023 holdout test set (5 unseen villages, 15 ground truth landslide episodes):
    - **Rainfall Baseline**: 160 episodes (32.0/vil/yr), POD 100.0%, FAR 90.62%, CSI 0.0938, Lead Time 29.6h.
    - **Global Threshold**: 112 episodes (22.4/vil/yr), POD 80.00%, FAR 89.29%, CSI 0.1043, Lead Time 1.08h.
    - **Per-Village Bayes-Optimal**: **63 episodes** (**12.6/vil/yr**), POD 73.33%, FAR **82.54%**, CSI **0.1642**, Lead Time 0.45h.
  - Honestly documented where per-village thresholds do worse in [`docs/RESULTS.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/RESULTS.md) (lower recall: 73.3% vs 80.0%/100%, tighter lead time: 0.45h vs 1.08h/29.6h in exchange for a 60% reduction in false alert burden and 75% higher CSI).
- **Database Model & Persistence (`backend/app/db/models.py`)**:
  - Added `VillageThreshold` table with unique foreign key to `villages.id`, storing costs, Bayes thresholds, multi-tier thresholds, annual caps, and JSON audit history.
  - Synced initial records for all 25 pilot villages via [`scripts/seed_data.py`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/scripts/seed_data.py).
- **Administrative REST Endpoints (`backend/app/api/endpoints/thresholds.py`)**:
  - `GET /api/v1/thresholds/{village_id}`: Retrieves active thresholds and audit history.
  - `PUT /api/v1/thresholds/{village_id}`: Allows district disaster officials to adjust thresholds with range validation ($0.001 \le p \le 0.999$, $\text{watch} < \text{warning} < \text{evacuate}$, $\text{cost} > 0$) and automated audit logging of modifications.
- **Unit & Integration Test Suite (`tests/test_thresholds.py`)**:
  - 6 unit tests covering cost sensitivity, clipping bounds, tier hierarchy, episode gap merging, GET 200/404, and PUT validation/audit logging.

---

### 2. How to Run and Test

#### Run Thresholds Unit Tests
```bash
python -m pytest tests/test_thresholds.py -v
```

#### Run Full Test Suite Across All Modules
```bash
python -m pytest tests/ -v
```

---

### 3. Verification Results
- **Full Test Suite**: **58/58 tests passed**:
  - `tests/test_evacuation.py`: 8 passed.
  - `tests/test_thresholds.py`: 6 passed.
  - `tests/test_uncertainty.py`: 6 passed.
  - `tests/test_analog.py`: 7 passed.
  - `tests/test_models.py`: 7 passed.
  - `tests/test_physics.py`: 6 passed.
  - `tests/test_connectors.py`: 7 passed.
  - `tests/test_ml_data.py`: 6 passed.
  - `tests/test_scaffold.py`: 5 passed.

---

## Task 10: Evacuation Route Optimization, Time-to-Impact & Multilingual Alerts (Completed)

### 1. What Was Done
- **Dynamic Time-to-Impact Estimator (`estimate_time_to_impact`)**:
  - Calculates lead-time range $[T_{\text{min}}, T_{\text{likely}}]$ combining nowcast rainfall intensity, rate of change $dR/dt$, and model calibrated failure probability trajectories.
- **NetworkX Evacuation Routing (`EvacuationNetworkRouter`)**:
  - Models mountain trails, intermediate junctions, and safe shelters with capacity checking.
  - Implements adjusted walking speed: base ~4.0 km/h (66.7 m/min), vulnerable demographic modifier ~2.0 km/h (33.3 m/min), night-time factor (1.4x), and trail hazard delay ($1.0 + 5.0 \times \text{cut\_risk}^2$).
  - Actively avoids segments exceeding cut-risk threshold ($0.60$) if alternative routes exist.
- **Available Margin & Stage Escalation (`determine_margin_alert_stage`)**:
  - Computes $\text{Margin} = T_{\text{likely}} - T_{\text{evacuate}}$.
  - Escalates earlier for narrow margins ($\le 15\text{m} \implies \text{EVACUATE}, \le 45\text{m} \implies \text{WARNING}, \le 120\text{m} \implies \text{WATCH}$).
- **Multilingual Alert Directives Under 160 Characters (`generate_alert_messages`)**:
  - One-line actionable message: `"Leave now. Go via {route} to {shelter}. You have about {margin} minutes."`
  - Strict length constraint asserted $\le 160$ chars across English (`en`), Hindi (`hi`), Garhwali (`gbm`), and Kumaoni (`kfy`).
  - Pluggable Bhashini API translation hook with graceful mock fallback.
- **Last-Mile Volunteer Task Cards (`generate_volunteer_task_cards`)**:
  - Links registered community volunteers to mobility-impaired/elderly households with specific safe paths, target shelters, and time windows.
- **API Endpoint (`POST /api/assess/{village_id}`)**:
  - Mounted directly at `/api/assess/{village_id}` (and `/api/v1/assess/{village_id}`) returning complete operational assessment.
- **Unit Test Suite (`tests/test_evacuation.py`)**:
  - 8 unit tests covering impact estimation, walking penalties, NetworkX routing, margin escalation, 160-char SMS assertions, Bhashini hook, volunteer cards, and FastAPI client endpoint validation.

---

### 2. How to Run and Test

#### Run Evacuation Unit Tests
```bash
python -m pytest tests/test_evacuation.py -v
```

#### Run Full Test Suite Across All Modules
```bash
python -m pytest tests/ -v
```

---

### 3. Verification Results
- **Full Test Suite**: **58/58 tests passed** across all 9 test suites.

---

## Task 11: Multi-Channel Alerting, CAP 1.2 XML, Fallback Ladder & Fatigue Control (Completed)

### 1. What Was Done
- **Pluggable Multi-Channel Delivery Adapters (`backend/app/services/alerting/adapters.py`)**:
  - Defined unified async `BaseChannelAdapter` returning standardized `DeliveryResult(success, delivery_id, channel, recipient_id, status, latency_ms, error, details)`.
  - Concrete channel implementations with realistic mountain propagation delay and simulated failure rate:
    1. `CellBroadcastMock`: Geo-fenced tower cellular broadcast (`CELL_BROADCAST`).
    2. `SMSMock`: Telecom SMS gateway (`SMS`).
    3. `WhatsAppMock`: Instant messaging channel (`WHATSAPP`).
    4. `IVRMock`: Automated voice call (`IVR`).
    5. `VolunteerTaskAdapter`: Last-mile volunteer task card dispatch (`VOLUNTEER`).
    6. `SirenMock`: Village high-decibel acoustic siren trigger (`SIREN`).
  - Swappable factory `get_channel_adapter(channel, failure_rate)` allowing seamless live provider replacement via config.
- **CAP 1.2 OASIS Standard XML Generation (`backend/app/services/alerting/cap.py`)**:
  - Implements official OASIS Common Alerting Protocol v1.2 XML format aligned with NDMA / SACHET standards.
  - Generates structured XML with `identifier`, `sender`, `sent`, `status` (`Actual` vs `Test`), `msgType`, `scope`, `info` block (urgency, severity, certainty, event, headline, description, instruction), and geo-fenced village area polygon coordinates.
- **Alert Fatigue Control & Suppression (`backend/app/services/alerting/fatigue.py`)**:
  - `check_alert_suppression`: Enforces a configurable cooldown period (default 60 minutes) between same-tier alerts for the same village.
  - Requires a strictly higher tier (e.g. `WATCH` -> `WARNING` -> `EVACUATE`) to override active cooldown.
  - `filter_recipients_by_safety`: Excludes residents confirmed in safe zones or shelters from repeated panic broadcasts.
- **Fallback Ladder Orchestrator (`backend/app/services/alerting/orchestrator.py`)**:
  - Cascading multi-tier alert ladder:
    1. Simultaneous `CELL_BROADCAST` and `SMS` to all eligible recipients.
    2. Configurable acknowledgement wait window (`escalation_window_sec`, default 300s).
    3. Unacknowledged recipients escalated to `IVR` voice call.
    4. Remaining unacknowledged recipients escalated to `VOLUNTEER` dispatch.
    5. `SIREN` acoustic trigger for critical `EVACUATE` directives or persistent unacknowledged citizens.
  - Logs every dispatch, failure, and acknowledgement into `alert_deliveries` table.
- **Live Delivery Reach & Drill Participation Metrics (`backend/app/services/alerting/metrics.py`)**:
  - `calculate_alert_reach`: Calculates real-time reach %, acknowledgment %, channel-by-channel breakdown (`SENT`, `ACKNOWLEDGED`, `FAILED`), and vulnerable demographic reach metrics.
  - `calculate_drill_report`: Evaluates community preparedness drill participation with compliance rating (`HIGH`, `MODERATE`, `LOW`).
- **REST API Endpoints (`backend/app/api/endpoints/alerting.py`)**:
  - `POST /api/alerts/trigger`: Trigger manual/automated alert with fatigue suppression check, CAP XML generation, and ladder execution.
  - `GET /api/alerts/{alert_id}/cap`: Retrieve OASIS CAP 1.2 XML document.
  - `POST /api/alerts/ack`: Acknowledge alert via delivery ID or recipient/alert ID.
  - `GET /api/alerts/{alert_id}/reach`: Live reach percentage and channel stats.
  - `POST /api/reports`: Citizen eye-witness hazard report submission (lat/lon, photo, text).
  - `GET /api/reports`: List community reports with status and ground-truth filtering.
  - `PUT /api/reports/{report_id}/review`: Vetting workflow marking observations as verified ground truth for ML retrain.
  - `POST /api/drills/trigger` & `GET /api/drills/{drill_id}/report`: Evacuation drill exercise trigger and compliance report.
- **Unit and Integration Test Suite (`tests/test_alerting.py`)**:
  - 12 comprehensive tests verifying adapters, simulated failures, factory, CAP 1.2 XML, drill XML, fatigue cooldown, safe zone filtering, ladder escalation, ack tracking, API triggers, community reports, and drill mode.

---

### 2. How to Run and Test

#### Run Alerting Tests
```bash
python -m pytest tests/test_alerting.py -v
```

#### Run Entire Repository Test Suite
```bash
python -m pytest tests/ -v
```

---

## Task 9: Citizen Ground-Truth Reporting Feature (Completed)

### 1. What Was Done
- **Database Model (`backend/app/db/models.py`)**:
  - Added `CitizenReport` table:
    - Primary key UUID `id`, `village_id` (foreign key to `villages.id`, nullable), `latitude`, `longitude`, `accuracy_meters`.
    - `media_type` (`'photo'` / `'video'`), `file_path`, `thumbnail_path`.
    - `caption`, `reported_flood` (boolean: True for flood active, False for false alarm/safe).
    - `reporter_phone` (stored securely, masked in responses).
    - `status` (`'pending'`, `'verified'`, `'rejected'`, `'duplicate'`), `created_at`, `reviewed_by`, `reviewed_at`, `audit_log`.
- **Upload & Media Validation (`backend/app/services/citizen_reports.py`)**:
  - File extension & MIME type validation: `.jpg`, `.jpeg`, `.png`, `.heic` (max 20MB) and `.mp4`, `.mov` (max 60MB). Rejecting any other extensions.
  - Safe segregated storage in `data/uploads/citizen_reports/{year}/{month}/` outside web root.
  - Auto-generated thumbnails: 320px JPEG thumbnails using Pillow for photos; ffmpeg extraction for videos with graceful fallback if ffmpeg is unavailable.
  - EXIF GPS Extraction & Complete Privacy Stripping: extracts EXIF GPS if coordinate params are omitted, and completely strips all camera/device EXIF metadata before disk write (DPDP Act 2023 compliance).
  - Reverse Spatial Mapping: Computes haversine distance to all seeded villages; maps to nearest village if $\le 25\text{km}$.
  - Abuse Protection: Rolling window rate limiter (max 5 reports per 15 minutes per IP or phone).
  - Computer Vision classifier stub hook for future automated flood depth and water boundary detection.
- **REST Endpoints (`backend/app/api/endpoints/citizen_reports.py`)**:
  - `POST /api/v1/reports/citizen`: Multipart submission endpoint.
  - `GET /api/v1/reports`: Filterable query endpoint (`village_id`, `status`, `since`, `reported_flood`, `limit`) with masked phone numbers.
  - `GET /api/v1/reports/{id}/media` & `GET /api/v1/reports/{id}/thumbnail`: Streaming file endpoints.
  - `PUT /api/v1/reports/{id}/status`: Officer review endpoint (`verified`, `rejected`, `duplicate`) with audit trail logging.
- **Frontend Mobile Citizen PWA (`frontend/src/pages/CitizenReportPage.tsx` & `/report` route)**:
  - Mobile-first single-tap UI with bilingual toggle (English and Hindi).
  - Camera & gallery upload supporting both photos and short videos.
  - Device GPS auto-fetch with manual coordinate fallback input.
  - Progress bar for uploads with XMLHttpRequest progress events.
  - Offline sync queue: locally queues reports in `localStorage` when network is disconnected and auto-synchronizes sequentially upon reconnection.
- **Officer Incident Dashboard & GIS Map**:
  - `VillageDetailPanel.tsx`: Added Citizen Ground-Truth Reports panel with thumbnail gallery, flood vs false alarm tags, distance from village center, and 1-click Verify/Reject controls.
  - `RiskMap.tsx`: Live MapLibre GeoJSON layer displaying citizen report pins with pulsing glow (Red = Flood Active, Green = Safe / False Alarm), interactive popup with photo preview, timestamp, GPS accuracy, and toggle in `LayerControl.tsx`.
- **Automated Tests (`tests/test_citizen_reports.py`)**:
  - 13 comprehensive tests covering valid uploads, video uploads, invalid types, oversized files, EXIF GPS extraction and stripping, village mapping within/outside 25km, rate limiting (429), filter queries, officer review & audit logging, and media streaming.

---

## Task 10: Product Rebranding to "Hyper-Local FlashFlood Prediction" (Completed)

### 1. What Was Done
- **Frontend App Title & Meta Description**:
  - Updated `frontend/index.html`:
    - `<title>` set to `"Hyper-Local FlashFlood Prediction — SIH 2026, PS 26192"`.
    - `<meta name="description">` set to `"Hyper-Local FlashFlood Prediction — SIH 2026, PS 26192"`.
- **PWA Manifest (`frontend/public/manifest.json`)**:
  - `name`: `"Hyper-Local FlashFlood Prediction"`.
  - `short_name`: `"FlashFlood EWS"`.
  - `description`: `"Hyper-Local FlashFlood Prediction & Evacuation Guidance — SIH 2026, PS 26192"`.
- **Mission Control Header & Brand Logo (`frontend/src/components/common/Header.tsx`)**:
  - Main title updated to `HYPER-LOCAL FLASHFLOOD PREDICTION`.
  - Subtitle badge updated to `SIH 2026, PS 26192`.
- **Citizen PWA (`frontend/src/pages/CitizenPWA.tsx`)**:
  - Header branding updated to `HYPER-LOCAL FLASHFLOOD PREDICTION` (English) and `हाइपर-लोकल फ्लैशबाढ़ पूर्वसूचना` (Hindi).
  - Subtitle updated to `SIH 2026, PS 26192 • Uttarkashi Pilot`.
  - Added `document.title` initialization to `"Hyper-Local FlashFlood Prediction — Citizen Advisory"`.
- **Citizen Report Page (`frontend/src/pages/CitizenReportPage.tsx`)**:
  - Added `document.title` initialization to `"Hyper-Local FlashFlood Prediction — Report"`.
- **Documentation Rebranding**:
  - `README.md`, `docs/README.md`, `docs/ARCHITECTURE.md`, `docs/DATA.md`, `docs/DEMO_SCRIPT.md`, and `docs/FRONTEND.md` updated with the new brand title and subtitle `"SIH 2026, PS 26192"`.
- **walkthrough.md**:
  - Rebranded title and references to `"Hyper-Local FlashFlood Prediction"`.

---

## Task 6: Enterprise-Grade Advanced AI, IoT Mesh, Dynamic Routing, Crisis Telecom & Decision Support (Completed)

### 1. What Was Implemented Across All 6 Dimensions
1. **Dimension 1: AI / Computer Vision & Satellite Remote Sensing**:
   - `FloodwaterSegmenter`: Color-space & texture variance segmentation for turbid Himalayan sediment-laden waters.
   - `StaffGaugeReader`: Horizontal Sobel edge gradient detection on staff gauges and bridge piers for depth estimation ($m$).
   - `DebrisVelocityEstimator`: Multi-frame optical flow displacement for supercritical debris torrent velocity ($m/s$).
   - `FalseAlarmClassifier`: Variance and chromatic balance filter rejecting benign scenes and blank screens.
   - `CVOrchestrator`: Full async inference pipeline mounted at `POST /api/v1/cv/analyze` and `POST /api/v1/cv/analyze/{report_id}`.
   - `CatchmentGNNModel` & `PINNResidualCorrector`: Directed stream graph across Upper Bhagirathi routing kinematic wave discharge $Q(t)$ and applying physics-informed residual pore-pressure reduction $\Delta F_s \in [0.0, 0.35]$.
   - `SatelliteRemoteSensing`: Sentinel-1 SAR/InSAR coherence loss, Sentinel-2 MNDWI water indices, NASA GPM IMERG nowcasts, and INSAT-3D rapid-scan TIR-1 $\Delta T_b / \Delta t < -15\text{K}/15\text{min}$ cloudburst detection.
2. **Dimension 2: IoT, Hardware & Multi-Hop Edge Mesh**:
   - `LoRaPacketCodec`: 16-byte packed binary frame codec for SX1262 / RAK4631 nodes with CRC-8 checksum.
   - `StoreAndForwardMeshGateway`: Mesh deduplication and store-and-forward queue with automatic MQTT bridge.
   - `InfrasoundGLOFDetector`: SM-24 class geophone & MEMS infrasound $1-30\text{Hz}$ acoustic rumble detector providing $15-30$ minute advance warning of impending GLOF surges.
   - `SolarPowerManager`: Sub-zero LiFePO4 battery protection halting charge below $0^\circ\text{C}$ to prevent lithium dendrites, with adaptive deep-sleep scheduling and `LAST_GASP` packet dispatch.
3. **Dimension 3: Dynamic Evacuation Routing & Real-Time Shelter Balancing**:
   - Multi-modal graph (Pedestrian Mountain Trails, 4x4 Jeep Roads, Helicopter Landing Zones).
   - Dynamic Dijkstra / A* routing with live edge cutoffs when river stage or landslide runouts intersect routes.
   - Real-time shelter load balancing: automatically diverts evacuees to the next optimal shelter when nearest shelter occupancy exceeds $90\%$ capacity.
4. **Dimension 4: Telecom, Satellite Broadcast & Extreme-Crisis Communications**:
   - `CDOTCellBroadcastEngine`: 3GPP TS 23.041 compliant geo-fenced Cell Broadcast Center (CBC) dispatch for local mobile BTS towers.
   - `NavICSatelliteMessenger`: Encodes ISRO NavIC (IRNSS) L5-band disaster alert packets with CRC-24 checksum.
   - `SatelliteBackhaulFailover`: Automated failover transitioning to BSNL Satellite IoT / Iridium SBD transceivers when terrestrial lines fail.
   - `BLEVictimTracker`: Aggregates peer-to-peer Bluetooth LE beacons emitted from trapped citizens under rubble.
5. **Dimension 5: Institutional Integration & Open Data Protocols**:
   - `CWCStageConnector`: Connects to Central Water Commission hydrological stations on Bhagirathi (Harsil, Uttarkashi, Tehri) tracking Danger level breaches.
   - `IMDDopplerRadarConnector`: Ingests Doppler reflectivity ($dBZ$) and computes rain rate via Marshall-Palmer $Z = 200 R^{1.6}$.
   - `NDMAPDNAGenerator`: Generates official NDMA-compliant Post-Disaster Needs Assessment (PDNA) reports across 5 core sectors.
   - `CommunityResilienceIndexCalculator`: Calculates Community Disaster Resilience Index (CDRI) scores across 5 core pillars.
6. **Dimension 6: Breakthrough UI/UX & Operator Decision Support**:
   - `CopilotDrawer`: Interactive AI Incident Copilot with live RAG, Situation Report (SITREP) generation, and human-in-the-loop tactical action cards.
   - `PDNAModal`: Sector-wise damage assessment matrix and exportable NDMA report modal.
   - `RiskMap`: MapLibre 3D Mountain Perspective camera controls ($58^\circ$ pitch) for Himalayan ridge visualization.

### 2. Verification and Test Results
- **Comprehensive PyTest Suite across all 6 Dimensions**:
  ```bash
  python -m pytest tests/test_ai_cv.py tests/test_satellite.py tests/test_mesh.py tests/test_dynamic_routing.py tests/test_telecom.py tests/test_institutional.py tests/test_copilot.py
  ```
  **Result:** `54 passed, 3 warnings in 167.71s` (100% test pass rate).
  - `tests/test_ai_cv.py`: 9/9 passed (water segmentation, staff gauge reader, optical flow, false-alarm filter, GNN catchment, PINN residual, endpoints).
  - `tests/test_satellite.py`: 7/7 passed (InSAR coherence, Sentinel-2 MNDWI, GPM IMERG, INSAT-3D TIR rapid-scan, risk fusion, endpoints).
  - `tests/test_mesh.py`: 9/9 passed (LoRa binary packet codec, CRC-8, store-and-forward gateway, geophone/infrasound TinyML GLOF rumble, subzero MPPT, endpoints).
  - `tests/test_dynamic_routing.py`: 6/6 passed (multi-modal network, edge cutoff on flood stage, >90% shelter load rebalancing, endpoints).
  - `tests/test_telecom.py`: 8/8 passed (C-DOT Cell Broadcast geo-fencing, NavIC L5 message encoding, satellite IoT failover, BLE victim beacon aggregator, endpoints).
  - `tests/test_institutional.py`: 8/8 passed (CWC river stage connector, IMD Doppler reflectivity, NDMA PDNA dossier generator, CDRI resilience index, endpoints).
  - `tests/test_copilot.py`: 7/7 passed (RAG incident assistant, SITREP generator, tool calling, endpoints).

- **Frontend Production Build**:
  ```bash
  npm run build
  ```
  **Result:** TypeScript compiler (`tsc`) and Vite production bundle passed cleanly with **0 errors**.

- **Detailed Technical Architecture Document**:
  - Full system design and API specification recorded in [`docs/new_features.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/new_features.md).

---

## Task 7: Officer Authentication, JWT RBAC & UI Action Gating (Completed)

### 1. What Was Implemented
1. **Backend Authentication & Officer RBAC Model**:
   - `Officer` SQLAlchemy model (`backend/app/db/models.py`) with `id`, `name`, `district`, `email`, `phone`, `role` (`officer` or `admin`), `password_hash`, `is_active`, `created_at`.
   - Secure password hashing using **bcrypt** with salt rounds (`backend/app/core/security.py`). Plain-text passwords are never stored or logged.
   - JWT tokens: 15-minute short-lived access tokens and 7-day refresh tokens signed with HS256.
   - Endpoints in `backend/app/api/endpoints/auth.py`:
     - `POST /api/v1/auth/login`: Authenticates via either official email or phone number + password; returns access token + sets `httpOnly` secure refresh cookie.
     - `POST /api/v1/auth/refresh`: Silently refreshes access token using httpOnly cookie.
     - `POST /api/v1/auth/logout`: Revokes refresh token cookie and invalidates session.
     - `GET /api/v1/auth/me`: Retrieves current officer profile and assigned role.
   - **Brute-Force Rate Limiting**: In-memory tracker enforcing a maximum of 5 failed login attempts per 10 minutes per IP before lockout.

2. **Protected Officer-Only Endpoints**:
   - `PUT /api/v1/thresholds/{village_id}`: Protected with `require_officer_role(["officer", "admin"])`.
   - `POST /api/v1/alerts/trigger`: Protected with `require_officer_role(["officer", "admin"])`.
   - `PUT /api/v1/reports/{report_id}/status`: Protected with `require_officer_role(["officer", "admin"])`.
   - `POST /api/v1/sensors/trust/reset`: Protected with `require_officer_role(["officer", "admin"])`.
   - Returns proper HTTP 401 Unauthorized for missing/invalid/expired tokens, and HTTP 403 Forbidden for unauthorized roles.
   - Public read-only endpoints (risk display, active alerts, health status) remain open without login.

3. **Seeded Pilot Accounts (`docs/DEMO_LOGINS.md`)**:
   - Seeded 3 demo officer accounts for the Uttarkashi pilot:
     - `ddmo.uttarkashi@uk.gov.in` / `Uttarkashi@2026` (Admin - Dr. Rajesh Sharma)
     - `ndrf.uttarkashi@gov.in` / `NDRF#Rescue2026` (Officer - Maj. Vikram Negi)
     - `bdo.bhatwari@uk.gov.in` / `Bhatwari@2026` (Officer - Pooja Rawat)
   - Created comprehensive security advisory in `docs/DEMO_LOGINS.md`.

4. **Frontend Integration & Token Security**:
   - `authService.ts`: Manages JWT access tokens in-memory (never in plain `localStorage`), supports silent refresh via `httpOnly` cookies or `/api/v1/auth/refresh`.
   - `AuthContext.tsx`: Provides reactive authentication state (`isOfficer`, `isAuthenticated`, `officer`, `login`, `logout`, `openLoginModal`).
   - `OfficerLoginModal.tsx`: Modal with 1-click Quick Demo profile buttons, manual credential input, password visibility toggle, and descriptive error banners.
   - Mounted `OfficerLoginModal` globally in `App.tsx`.
   - `Header.tsx`: Displays logged-in state (officer name, district, role badge, and red Logout button). When unauthenticated, shows prominent "Officer Login" button.

5. **Gated Officer-Only UI Actions**:
   - **Alert Dispatch**: "DISPATCH ALERT" in header and "ISSUE EVACUATION DIRECTIVE" in `VillageDetailPanel` and `AlertCreationModal` prompt officer login when unauthenticated.
   - **Citizen Report Verification**: "VET GROUND TRUTH" and "REJECT" buttons in `ReportsPage` and `VillageDetailPanel` show lock cues and prompt officer login when unauthenticated.
   - **Threshold Calibration**: Added Bayes-optimal operational threshold calibration card in `VillageDetailPanel` allowing officers to calibrate Watch, Warning, and Evacuate trigger probabilities with live backend persistence (`PUT /api/v1/thresholds/{village_id}`).

### 2. Verification and Test Results
- **Authentication Unit & Integration Tests (`tests/test_auth.py`)**:
  - `test_login_success_with_email`: PASSED
  - `test_login_success_with_phone`: PASSED
  - `test_login_invalid_password`: PASSED
  - `test_login_nonexistent_user`: PASSED
  - `test_login_brute_force_rate_limit`: PASSED (locks out after 5 consecutive failures)
  - `test_refresh_token_endpoint`: PASSED
  - `test_logout_endpoint`: PASSED
  - `test_protected_endpoint_without_token_fails`: PASSED (HTTP 401)
  - `test_protected_endpoint_invalid_token_fails`: PASSED (HTTP 401)
  - `test_protected_endpoint_expired_token_fails`: PASSED (HTTP 401)
  - `test_protected_endpoint_with_valid_officer_token`: PASSED (HTTP 200)
  - `test_get_current_officer_me`: PASSED (HTTP 200)
  - **Result**: `12 passed in 10.42s`.

- **Frontend Production Build**:
  - `tsc && vite build`: **0 errors**, production bundle generated cleanly.

---

## Task 8: Dual Light/Dark Theme Engine (Light Default) (Completed)

### 1. What Was Implemented
1. **CSS Variable-Based Theme Architecture**:
   - Configured dual theme palettes in `frontend/src/index.css` via `:root` (Light) and `html.dark` (Dark).
   - Variables define backgrounds (`--bg-primary`, `--bg-secondary`, `--bg-card`), borders (`--border-color`), typography (`--text-primary`, `--text-secondary`), chart tokens (`--chart-grid`, `--chart-axis`), and risk tier tokens.
   - Comprehensive light-mode global override rules ensuring seamless light rendering across all legacy slate components when `.dark` is absent, and dark slate when `.dark` is present.
   - Zero-flicker bootstrapper in `frontend/index.html` executing synchronously before DOM rendering.

2. **Strict Light Default on First Load**:
   - First-time visitors are guaranteed to load in **Light Theme**, completely decoupled from OS `prefers-color-scheme`.
   - Subsequent user selections are remembered in `localStorage` under `ews_theme` (`'light'` | `'dark'`).

3. **Instant Zero-Reload Theme Toggle**:
   - Created `ThemeContext` (`frontend/src/context/ThemeContext.tsx`) mounted at the root application tree.
   - Header toggle button with reactive Sun/Moon icon (`frontend/src/components/common/Header.tsx`).
   - Citizen interfaces (`CitizenReportPage.tsx` and `CitizenPWA.tsx`) include dedicated theme toggles in their respective headers.
   - Toggling updates DOM `classList` and `data-theme` attribute instantly without any page reload or state loss.

4. **MapLibre GL Dual Basemap Switching**:
   - In `RiskMap.tsx`, dynamic basemap tile swap between **Carto Positron** (light) and **Carto Dark Matter** (dark).
   - Implemented reactive `useEffect` utilizing `map.getSource('osm-tiles').setTiles()` so toggling theme instantly updates the underlying raster basemap without recreating the map instance or losing GeoJSON vectors, route layers, or popups.

5. **SVG Trajectory Chart Dynamic Adaptability**:
   - `RiskTimeline.tsx` dynamically adapts grid lines, axes lines, labels, and the current-time indicator based on active theme colors.

6. **WCAG AA / AAA Color Contrast Compliance**:
   - High-contrast risk tier palette across `WATCH` (amber), `WARNING` (orange), `EVACUATE` (red), and `SAFE` (emerald).
   - In Light Mode, uses deep saturated text on pastel pill backgrounds (`#991b1b` on `#fef2f2`, ratio 7.28:1 - AAA).
   - In Dark Mode, uses luminous text on translucent dark backgrounds (`#fca5a5` on `rgba(127, 29, 29, 0.55)`, ratio 8.63:1 - AAA).

7. **Documentation & Verification Matrix**:
   - Documented complete screen-by-screen checklist and contrast audit in [`docs/THEME_CHECKLIST.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/THEME_CHECKLIST.md).

### 2. Verification and Test Results
- **Frontend Production Build**:
  - `npm run build`: `tsc && vite build` built cleanly with **0 errors**.
- **Visual & Contrast Verification**:
  - Verified across Command Center, Live Risk Map, Village Dossier Panel, Alert Center, Citizen Report Form, Citizen PWA, Officer Login Modal, Alert Dispatch Modal, and PDNA Modal.
  - All risk tiers exceed WCAG 2.1 Level AA (4.5:1 ratio).

---

## Task 9: Comprehensive UX, Accessibility, and Performance Overhaul (Completed)

### 1. What Was Implemented
1. **Toast Notification Architecture & Action Feedback**:
   - Built application-wide `ToastContext` (`ToastProvider` + `useToast()`) with floating auto-dismissing notifications for success, error, warning, and info states.
   - Connected to officer login/logout, alert dispatching, threshold calibrations, citizen report submissions, and shelter check-ins.
   - Created animated `Skeleton` components for cards, tables, and dossiers.

2. **Interactive Map UX Enhancements (`RiskMap.tsx`)**:
   - Interactive hover tooltips displaying village name, WCAG AA tier pill, population, and real-time risk probability.
   - Distinct visual highlight for selected village: ambient halo glow (`villages-selected-glow`) and white double-ring stroke (`villages-selected-ring`).
   - Smooth slide-in animation (`animate-slide-in-right`) when opening the village dossier panel.

3. **Mobile Responsiveness & 375px Viewport Audit**:
   - Compact, non-wrapping header bar on mobile viewports.
   - Sticky bottom submission bar on `CitizenReportPage.tsx` for effortless one-handed thumb interaction on mobile devices.
   - Responsive village dossier panel rendering as a full-width overlay drawer on mobile screens with accessible close buttons.

4. **Friendly Empty and Error States (`EmptyState.tsx`)**:
   - Reusable `EmptyState` component integrated into `AlertsPage`, `ReportsPage`, `SensorsPage`, and `VillageDetailPanel` providing clear guidance and call-to-actions when lists are empty or offline.

5. **Accessibility (a11y) Upgrades**:
   - Explicit `aria-label` attributes on all icon-only buttons (theme toggle, close dialogs, toast dismiss, alert dispatch).
   - High-contrast visible focus rings (`focus-visible:ring-2 focus-visible:ring-orange-500`).
   - Keyboard `Escape` key listeners on modals and forms.

6. **Bilingual Micro-Copy Refinement**:
   - Replaced technical jargon with compassionate, plain-language English and natural Hindi phrasing across citizen-facing pages.

7. **Performance & Route-Level Code Splitting**:
   - Converted all 16 page routes to `React.lazy()` with `Suspense` and an app-level branded `<AppLoadingScreen />`.
   - Initial JavaScript bundle reduced from **1,271 kB** to **260 kB** (79.79 kB gzipped) — a **79.5% reduction** in initial load weight.

8. **Documentation**:
   - Full detailed changelog logged in [`docs/UX_CHANGES.md`](file:///c:/Users/shukl/OneDrive/Desktop/PS192/docs/UX_CHANGES.md).


