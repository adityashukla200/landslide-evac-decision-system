# Manual Data Ingestion & External Sources Guide

This guide details the procurement, clipping, and directory layout for real-world geospatial and remote sensing inputs for the **Uttarkashi pilot district**.

---

## 1. District Bounding Box Specification

All regional rasters and spatial inventories must be clipped to the Uttarkashi district watershed envelope before ingestion:

```yaml
Bounding Box:
  CRS: EPSG:4326 (WGS 84)
  Min Longitude (West):  77.85° E
  Min Latitude  (South): 30.45° N
  Max Longitude (East):  79.15° E
  Max Latitude  (North): 31.45° N
```

Use the automated clipping utility to crop raw national/regional downloads:
```bash
python scripts/clip_to_district.py --input /path/to/downloaded_raster.tif --output data/raw/dem/srtm_30m.tif
```

---

## 2. Source Procurement & Target Directory Stubs

| Source | Provider & Portal | Format | Target Drop Directory | Auto-Detected By |
| :--- | :--- | :--- | :--- | :--- |
| **Digital Elevation Model (DEM)** | NASA SRTM 30m (GL1) or ISRO Bhuvan Cartosat-1 (30m) | GeoTIFF / CSV | `/data/raw/dem/` | `load_dem()` |
| **Landslide Inventory** | Geological Survey of India (GSI) Bhukosh Portal | CSV (`lat, lon, date, type`) | `/data/raw/landslides/` | `load_landslide_inventory()` |
| **Gridded Rainfall** | India Meteorological Department (IMD) 0.25° Gridded Rainfall | NetCDF / CSV / Parquet | `/data/raw/rainfall/` | `load_rainfall()` |
| **Satellite Precipitation** | NASA GPM IMERG Early/Late Run (0.1° via Earthdata) | NetCDF4 / GeoTIFF / Parquet | `/data/raw/rainfall/` | `load_rainfall()` |
| **Soil Moisture** | ESA CCI Soil Moisture / SMAP L4 | GeoTIFF / NetCDF / CSV | `/data/raw/soil_moisture/` | `load_soil_moisture()` |
| **Optical / SAR Imagery** | ESA Copernicus Sentinel-2 (NDVI) & Sentinel-1 (C-band GRD) | GeoTIFF / Parquet | `/data/raw/land_use/` | `load_land_use()` |

---

## 3. Step-by-Step Acquisition Instructions

### A. Digital Elevation Model (SRTM 30m)
1. Visit **USGS EarthExplorer** (`earthexplorer.usgs.gov`) or **NASA Earthdata Search**.
2. Set bounding box to `[77.85, 30.45, 79.15, 31.45]`.
3. Select dataset: `Digital Elevation -> SRTM -> SRTM 1 Arc-Second Global`.
4. Download GeoTIFF tile `n30_e078_1arc_v3.tif` and `n31_e078_1arc_v3.tif`.
5. Clip and place in `data/raw/dem/`:
   ```bash
   python scripts/clip_to_district.py --input n30_e078_1arc_v3.tif --output data/raw/dem/srtm_uttarkashi.tif
   ```

### B. GSI Bhukosh Landslide Inventory
1. Visit **Bhukosh - Geological Survey of India** (`bhukosh.gsi.gov.in`).
2. Navigate to `Geohazards -> Landslide Incident Data`.
3. Query district: `Uttarakhand -> Uttarkashi`.
4. Export as CSV / Shapefile.
5. Ensure column names map to: `lat, lon, date, type` (e.g. `debris_flow`, `rockfall`, `shallow_translational`).
6. Save file directly as:
   `data/raw/landslides/landslide_inventory.csv`

### C. IMD Gridded Rainfall & GPM IMERG
1. Download 0.25° IMD binary or NetCDF files from **IMD Pune Climate Services**.
2. Alternatively, download half-hourly GPM IMERG files from **NASA GES DISC** (`disc.gsfc.nasa.gov`).
3. Convert or extract time series for the 25 village locations and drop as:
   `data/raw/rainfall/rainfall_observations.parquet` (or `.csv`).

### D. Sentinel-1 & Sentinel-2 Optical (NDVI)
1. Download Sentinel-2 L2A bottom-of-atmosphere surface reflectance from **Copernicus Open Access Hub / Browser**.
2. Compute NDVI:
   $$\text{NDVI} = \frac{\text{B08 (NIR)} - \text{B04 (Red)}}{\text{B08 (NIR)} + \text{B04 (Red)}}$$
3. Clip to district and save to:
   `data/raw/land_use/ndvi_sentinel2.parquet` (or `.tif`).

---

## 4. Automatic Zero-Config Fallback Behavior

If any of the above manual directories are empty or missing:
- The system automatically triggers the physics-guided synthetic generator from `ml/data/synthetic.py`.
- No exceptions are thrown; the system runs completely offline.
- Every API record and model output reports `data_source: "SIMULATED"` so operators always know the data origin.
