"""Utility script to clip external regional rasters, vectors, or catalogs to the Uttarkashi district bounding box.

Bounding Box (Uttarkashi District + Catchment Buffer):
- Min Longitude: 77.85°E
- Min Latitude:  30.45°N
- Max Longitude: 79.15°E
- Max Latitude:  31.45°N
"""

import sys
import argparse
from pathlib import Path
from typing import Tuple, Optional
import pandas as pd
import numpy as np

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Uttarkashi district catchment bounding box
UTTARKASHI_BBOX = {
    "min_lon": 77.85,
    "min_lat": 30.45,
    "max_lon": 79.15,
    "max_lat": 31.45,
}


def clip_csv_or_parquet(input_path: Path, output_path: Path) -> int:
    """Filter tabular geospatial points to the Uttarkashi bounding box."""
    if input_path.suffix == ".parquet":
        df = pd.read_parquet(input_path)
    else:
        df = pd.read_csv(input_path)

    # Detect coordinate column names
    lat_col = next((c for c in df.columns if c.lower() in ["lat", "latitude", "y"]), None)
    lon_col = next((c for c in df.columns if c.lower() in ["lon", "long", "longitude", "x"]), None)

    if not lat_col or not lon_col:
        raise ValueError(f"Could not identify latitude/longitude columns in {input_path.name}")

    initial_len = len(df)
    clipped = df[
        (df[lat_col] >= UTTARKASHI_BBOX["min_lat"])
        & (df[lat_col] <= UTTARKASHI_BBOX["max_lat"])
        & (df[lon_col] >= UTTARKASHI_BBOX["min_lon"])
        & (df[lon_col] <= UTTARKASHI_BBOX["max_lon"])
    ]
    clipped_len = len(clipped)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.suffix == ".parquet":
        clipped.to_parquet(output_path, index=False)
    else:
        clipped.to_csv(output_path, index=False)

    print(f"[+] Clipped {initial_len:,} rows -> {clipped_len:,} rows within Uttarkashi BBOX. Saved to {output_path}")
    return clipped_len


def clip_raster(input_path: Path, output_path: Path) -> None:
    """Clip a GeoTIFF or NetCDF raster to the Uttarkashi bounding box."""
    try:
        import rasterio
        from rasterio.windows import from_bounds
        from rasterio.warp import transform_bounds

        with rasterio.open(input_path) as src:
            # Transform bounds to raster CRS if not EPSG:4326
            if src.crs != "EPSG:4326":
                bbox = transform_bounds(
                    "EPSG:4326", src.crs,
                    UTTARKASHI_BBOX["min_lon"], UTTARKASHI_BBOX["min_lat"],
                    UTTARKASHI_BBOX["max_lon"], UTTARKASHI_BBOX["max_lat"]
                )
            else:
                bbox = (
                    UTTARKASHI_BBOX["min_lon"], UTTARKASHI_BBOX["min_lat"],
                    UTTARKASHI_BBOX["max_lon"], UTTARKASHI_BBOX["max_lat"]
                )

            window = from_bounds(*bbox, transform=src.transform)
            transform = src.window_transform(window)
            data = src.read(window=window)

            profile = src.profile.copy()
            profile.update({
                "height": data.shape[1],
                "width": data.shape[2],
                "transform": transform,
            })

            output_path.parent.mkdir(parents=True, exist_ok=True)
            with rasterio.open(output_path, "w", **profile) as dst:
                dst.write(data)

            print(f"[+] Raster clipped to shape {data.shape}. Saved to {output_path}")

    except ImportError:
        print("[!] rasterio library not installed. Generating dummy metadata clip...")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Write metadata placeholder for manual workflow
        meta_info = f"# Clipped bbox: {UTTARKASHI_BBOX}\n# Original source: {input_path}\n"
        output_path.write_text(meta_info)
        print(f"[+] Written placeholder clip config to {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Clip geospatial files to Uttarkashi district bbox.")
    parser.add_argument("--input", required=True, type=str, help="Path to input raster/table")
    parser.add_argument("--output", required=False, type=str, help="Path to output clipped file")
    args = parser.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[!] Error: Input file '{in_path}' does not exist.")
        sys.exit(1)

    out_path = Path(args.output) if args.output else in_path.parent / f"clipped_{in_path.name}"

    if in_path.suffix.lower() in [".csv", ".parquet"]:
        clip_csv_or_parquet(in_path, out_path)
    elif in_path.suffix.lower() in [".tif", ".tiff", ".nc"]:
        clip_raster(in_path, out_path)
    else:
        print(f"[!] Unsupported format '{in_path.suffix}'. Only .csv, .parquet, .tif, .nc supported.")
        sys.exit(1)


if __name__ == "__main__":
    main()
