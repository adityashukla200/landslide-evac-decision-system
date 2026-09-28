# REST & MQTT API Reference Manual

> **SIH 2026 Problem Statement 26192**  
> Base URL: `http://localhost:8000` | API Prefix: `/api/v1`  
> OpenAPI Interactive Swagger UI: `http://localhost:8000/docs`

---

## 1. Authentication & Security Headers

All requests can supply identity and authorization headers:

| Header | Description | Default / Example |
|---|---|---|
| `X-User-Role` | Declares user privilege tier: `officer`, `volunteer`, `citizen` | Defaults to `officer` in local demo |
| `Authorization` | Standard Bearer token or API key | `Bearer officer-session-token` |
| `X-RateLimit-Limit` | Maximum permitted requests per minute (Response header) | `180` |
| `X-RateLimit-Remaining` | Remaining request quota in current 60s sliding window | `179` |

---

## 2. Core Endpoints Summary

### 2.1 System & Health

#### `GET /health`
Verifies database connectivity (SQLite/PostgreSQL) and Redis cache status.
```json
{
  "status": "ok",
  "database": "connected",
  "redis": "connected",
  "database_type": "sqlite",
  "version": "0.1.0",
  "environment": "development",
  "timestamp": 1727546700.12
}
```

---

### 2.2 Security & RBAC (`/api/v1/security`)

#### `GET /api/v1/security/whoami`
Returns active role, permissions, and DPDP compliance notice.
- **Headers**: `X-User-Role: officer | volunteer | citizen`
```json
{
  "role": "officer",
  "privileges": [
    "trigger_emergency_alert",
    "modify_operational_thresholds",
    "initiate_evacuation_order",
    "dispatch_ndrf_teams",
    "view_unmasked_pii",
    "view_command_center"
  ],
  "status": "authenticated",
  "privacy_policy": "Compliant with DPDP Act 2023. PII is masked by default on all public endpoints."
}
```

#### `POST /api/v1/security/officer-only-action`
Restricted endpoint requiring `officer` role. Returns HTTP 403 Forbidden for `volunteer` or `citizen`.

---

### 2.3 Sensor Subsystem (`/api/v1/sensors`)

#### `GET /api/v1/sensors/registry`
Returns the 25 Himalayan village sensor installations with coordinates, elevation, and equipment status.

#### `POST /api/v1/sensors/simulate/step`
Advances the 25-village IoT simulator one 5-minute tick, runs the 5-rule Sensor Trust Layer, and computes virtual sensor estimates.
```json
{
  "timestamp": "2026-09-28T22:15:00Z",
  "seq": 42,
  "raw_count": 69,
  "trust_summary": {
    "OK": 64,
    "SUSPECT": 3,
    "DEGRADED": 0,
    "REJECTED": 2,
    "dropout_skipped": 3
  },
  "virtual_count": 28
}
```

#### `GET /api/v1/sensors/readings/latest?village_id=V01&sensor_type=soil_moisture`
Returns trusted sensor readings filtered by village or sensor type.

#### `GET /api/v1/sensors/virtual?village_id=V19`
Returns spatial Inverse-Distance-Weighted (IDW) estimates with orographic elevation correction and $1\sigma$ uncertainty for unequipped settlements.

#### `GET /api/v1/sensors/cross-validate?sensor_type=soil_moisture`
Executes leave-one-out cross validation (LOO-CV) across equipped villages.

---

### 2.4 Operational Risk Thresholds (`/api/v1/thresholds`)

#### `GET /api/v1/thresholds/{village_id}`
Returns Bayes-optimal operating thresholds, relative loss weights ($C_{\text{miss}}, C_{\text{false\_alarm}}$), and historical audit logs.

#### `PUT /api/v1/thresholds/{village_id}`
*(Requires role: `officer`)* Updates operational thresholds with audit tracking.
```json
{
  "watch_threshold": 0.015,
  "warning_threshold": 0.025,
  "evacuate_threshold": 0.120,
  "change_reason": "Monsoon orange alert issued by IMD for Bhagirathi catchment"
}
```

---

### 2.5 Evacuation & Hazard Assessment (`/api/v1/evacuation` & `/api/assess`)

#### `GET /api/assess/{village_id}`
Comprehensive evacuation assessment:
- Rainfall acceleration and nowcast trend
- Dynamic time-to-impact $[T_{\text{min}}, T_{\text{likely}}]$
- Walking durations adjusted for vulnerable citizens ($33.3\ \text{m/min}$) and night time ($+40\%$)
- Topological route selection avoiding severed segments
- Multilingual alert text in English, Hindi, Garhwali, and Kumaoni ($\le 160$ chars).

---

### 2.6 Multi-Channel Alerting Ladder (`/api/v1/alerting` & `/api/alerts`)

#### `POST /api/alerts/trigger`
*(Requires role: `officer`)* Initiates the multi-channel escalation ladder:
1. Generates CAP 1.2 XML with geographic polygon geofencing.
2. Dispatches Cell Broadcast $\to$ SMS.
3. Awaits 5-minute citizen acknowledgement.
4. Escalates to IVR phone calls $\to$ Volunteer task cards $\to$ Acoustic sirens.

#### `POST /api/alerts/ack`
Citizen/volunteer acknowledgement tracking (`delivered`, `read`, `evacuating`, `safe`).

#### `GET /api/alerts/reach/{village_id}`
Returns live delivery percentage and reach stats per village.

---

### 2.7 Disaster Replay Engine (`/api/v1/replay`)

#### `GET /api/v1/replay/scenarios`
Lists available historical/synthetic calibration scenarios (`bhatwari_debris_flow_synthetic`, `harsil_flash_flood_synthetic`).

#### `POST /api/v1/replay/run`
Fast-forwards scenario timeline through features, physics $F_s$, ML probability, Venn-Abers bounds, and alerting ladder.
- **Payload**:
  ```json
  {
    "scenario_id": "bhatwari_debris_flow_synthetic",
    "kill_internet": false,
    "speed_multiplier": 2.0
  }
  ```
- **Returns**: Frame-by-frame audit dossier comparing AI EWS vs IMD static baseline lead time gain.

---

## 3. MQTT IoT Topic Specification

For edge sensor telemetry and LoRa base station relays:

| Topic Pattern | Direction | Payload Schema | Description |
|---|---|---|---|
| `sensors/{village_id}/soil_moisture` | Publish | `{"value": 0.65, "unit": "m3/m3", "seq": 101, "timestamp": "..."}` | Volumetric water content |
| `sensors/{village_id}/rainfall` | Publish | `{"value": 4.2, "unit": "mm", "seq": 101, "timestamp": "..."}` | 5-minute accumulation |
| `sensors/{village_id}/tilt` | Publish | `{"value": 0.42, "unit": "deg", "seq": 101, "timestamp": "..."}` | Inclinometer deviation |
| `sensors/{village_id}/stream_level` | Publish | `{"value": 2.15, "unit": "m", "seq": 101, "timestamp": "..."}` | Ultrasonic stream gauge |
| `ews/alerts/{village_id}` | Subscribe | `{"tier": "EVACUATE", "route": "Route B", "siren": true}` | Edge actuator trigger |
| `ews/ota/{village_id}` | Subscribe | `{"version": "1.4.2", "firmware_url": "..."}` | ESP32 Over-the-Air update |
