# Citizen Ground-Truth Reporting Feature

## 1. Overview & Architecture

The **Citizen Ground-Truth Reporting** subsystem enables residents, ward volunteers, and field staff across the Uttarkashi Catchment region to submit real-time ground observations with geotagged photos or short videos. This provides critical ground-truth verification for the Early Warning System (EWS), enabling disaster management authorities to:
- Confirm active flash floods or landslide surges.
- Detect and cancel false alarms rapidly ("No flood here, stream is normal").
- Calibrate hydrologic model predictions with hyper-local field observations.

```
+-------------------------------------------------------------+
|                     Citizen PWA (/report)                   |
|  - Camera Photo / Video Capture (HTML5 File API)            |
|  - High-Accuracy GPS Auto-Fetch + Manual Fallback           |
|  - Bilingual (English / Hindi) Single-Tap Interface         |
|  - Offline Indexed/Local Queue with Auto-Sync Reconnection  |
+------------------------------+------------------------------+
                               |
                               | Multipart Form-Data POST
                               v
+-------------------------------------------------------------+
|               FastAPI Backend (/api/v1/reports)             |
|  - Rate Limiter: 5 reports / 15 min per IP/Phone            |
|  - Format & Size Validation (Photo <=20MB, Video <=60MB)     |
|  - EXIF GPS Extraction + Strict EXIF Stripping (Privacy)    |
|  - Thumbnail Generation (Pillow / ffmpeg with fallback)     |
|  - Reverse-Spatial Mapping to Village (<=25km Haversine)     |
|  - Future ML Auto-Classifier Hook                           |
+------------------------------+------------------------------+
                               |
                               v
+-------------------------------------------------------------+
|              Storage & Officer Decision Systems             |
|  - Storage: /data/uploads/citizen_reports/{year}/{month}/   |
|  - SQLite/PostgreSQL: citizen_reports Table                 |
|  - Officer Dashboard: RiskMap GeoJSON layer & Village Panel |
+-------------------------------------------------------------+
```

---

## 2. Database Schema (`citizen_reports`)

Defined in `backend/app/db/models.py`:

| Column | Type | Nullable | Description |
|---|---|---|---|
| `id` | `VARCHAR(36)` | No | UUID primary key (e.g., `cr_c56b4618e7d4...`) |
| `village_id` | `VARCHAR(32)` | Yes | Foreign key to `villages.id` (nearest village within 25km) |
| `latitude` | `FLOAT` | No | Geotagged latitude (-90 to 90) |
| `longitude` | `FLOAT` | No | Geotagged longitude (-180 to 180) |
| `accuracy_meters`| `FLOAT` | Yes | GPS horizontal accuracy reported by device |
| `media_type` | `VARCHAR(16)` | No | `'photo'` or `'video'` |
| `file_path` | `VARCHAR(512)` | No | Relative server file path |
| `thumbnail_path`| `VARCHAR(512)` | Yes | Relative server thumbnail path |
| `caption` | `TEXT` | Yes | Citizen description or notes |
| `reported_flood`| `BOOLEAN` | No | `True` (Flood happening) vs `False` (Safe / False alarm) |
| `reporter_phone`| `VARCHAR(32)` | Yes | Raw phone number (masked in public API responses) |
| `status` | `VARCHAR(32)` | No | `'pending'`, `'verified'`, `'rejected'`, `'duplicate'` |
| `created_at` | `DATETIME` | No | Timestamp of submission |
| `reviewed_by` | `VARCHAR(64)` | Yes | Officer name / ID who reviewed |
| `reviewed_at` | `DATETIME` | Yes | Timestamp of officer action |
| `audit_log` | `JSON` | Yes | List of officer review events & timestamps |

---

## 3. API Specification

### 3.1 Submit Citizen Report
- **Endpoint:** `POST /api/v1/reports/citizen`
- **Content-Type:** `multipart/form-data`
- **Parameters:**
  - `file` (UploadFile, required): Image (`.jpg`, `.jpeg`, `.png`, `.heic`, max 20MB) or Video (`.mp4`, `.mov`, max 60MB).
  - `latitude` (float, optional if embedded in EXIF GPS): Geolocation latitude.
  - `longitude` (float, optional if embedded in EXIF GPS): Geolocation longitude.
  - `accuracy_meters` (float, optional): Device GPS accuracy.
  - `reported_flood` (bool, required): `true` for flood active, `false` for false alarm / safe.
  - `caption` (str, optional, max 500 chars): Text description.
  - `reporter_phone` (str, optional): Phone number for follow-up.
- **Response:** `201 Created`
  ```json
  {
    "status": "success",
    "message": "Report submitted successfully. Thank you for contributing ground truth.",
    "report_id": "cr_c56b4618e7d4...",
    "village_id": "VIL_UTK_07",
    "village_name": "Bhatwari",
    "distance_from_village_km": 0.82,
    "latitude": 30.816,
    "longitude": 78.62,
    "media_type": "photo",
    "media_url": "/api/v1/reports/cr_c56b4618e7d4.../media",
    "thumbnail_url": "/api/v1/reports/cr_c56b4618e7d4.../thumbnail",
    "reported_flood": true,
    "review_status": "pending",
    "created_at": "2026-09-29T07:15:32.123456"
  }
  ```

### 3.2 Query Citizen Reports
- **Endpoint:** `GET /api/v1/reports`
- **Query Parameters:**
  - `village_id`: Filter by assigned village ID.
  - `status`: Filter by `'pending'`, `'verified'`, `'rejected'`, or `'duplicate'`.
  - `reported_flood`: Filter by boolean (`true` or `false`).
  - `since`: ISO datetime string (e.g. `2026-09-29T00:00:00Z`).
  - `limit`: Integer (1 to 500, default 100).
- **Response:** `200 OK` (Array of report objects with masked phone numbers).

### 3.3 Media Streaming
- **Endpoint:** `GET /api/v1/reports/{report_id}/media`
- **Description:** Streams the validated media file directly from protected server storage. Disallows direct web root browsing.

### 3.4 Thumbnail Streaming
- **Endpoint:** `GET /api/v1/reports/{report_id}/thumbnail`
- **Description:** Streams the auto-generated 320px thumbnail (JPEG).

### 3.5 Officer Status Review
- **Endpoint:** `PUT /api/v1/reports/{report_id}/status`
- **Body:**
  ```json
  {
    "status": "verified",
    "reviewed_by": "District Magistrate / Officer 04",
    "notes": "Confirmed flash flood near river bank."
  }
  ```
- **Response:** `200 OK` with updated review status and audit log record.

---

## 4. Privacy, Security & Compliance

### 4.1 Digital Personal Data Protection (DPDP) Act 2023 Compliance
1. **EXIF Stripping:** When citizens upload photographs containing GPS and camera metadata, the backend extracts latitude/longitude (if not supplied in the form) and then **strips all EXIF metadata completely** using Pillow before saving to disk. This prevents device fingerprints, timestamps, and personal metadata from being exposed.
2. **Phone Number Masking:** The reporter's phone number is restricted to internal operational use and masked in all API responses (e.g., `+91 98*** **210`).
3. **Protected File Storage:** Files are stored in `data/uploads/citizen_reports/{year}/{month}/`, entirely outside any static web server root. Access is mediated exclusively through `/api/v1/reports/{id}/media` with access controls.
4. **Abuse Prevention & Rate Limiting:** A rolling in-memory rate limiter restricts submissions to **5 reports per 15 minutes** per IP address or phone number, returning `429 Too Many Requests` when exceeded.

---

## 5. Offline PWA & Synchronization

For mountainous terrain with intermittent connectivity:
- The citizen interface `/report` captures submissions even when offline.
- Submissions are queued in browser `localStorage` as base64-encoded packages.
- When `window.addEventListener('online', ...)` triggers or the user re-opens the app, the background queue synchronizes pending reports in sequential batches.
- Bilingual toggle (English and Hindi) ensures high accessibility across local communities.

---

## 6. Officer Decision Dashboard & GIS Integration

- **Village Detail Panel:** Displays recent ground-truth reports for the selected village, thumbnail previews, flood/safe status tags, distance from village center, and 1-click **Verify** or **Reject** controls.
- **Interactive GIS Map (`RiskMap.tsx`):**
  - Displays geotagged citizen reports as map pins with pulsing glows.
  - Color-coded: Red (`#ef4444`) for active flood reports; Green (`#10b981`) for safe / false alarm reports.
  - Interactive popup displays thumbnail photo, hazard badge, GPS accuracy, caption, and timestamp.
  - Toggleable via the **GIS Map Layers** control.
