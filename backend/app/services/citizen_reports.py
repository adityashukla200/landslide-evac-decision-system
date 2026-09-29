"""Service module for citizen ground-truth reports: media validation, EXIF stripping,
thumbnail generation, nearest-village reverse mapping, and abuse protection.
"""

from __future__ import annotations

import io
import math
import time
import uuid
import shutil
import logging
import subprocess
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple, Deque, List, Any

from fastapi import UploadFile, HTTPException, status
from PIL import Image
from sqlalchemy.orm import Session

from backend.app.core.config import settings, ROOT_DIR
from backend.app.db.models import Village, CitizenReport
from backend.app.core.security import mask_phone_number

logger = logging.getLogger(__name__)

# TODO: Future work - ML computer vision auto-classifier for flood depth, debris flow presence, and road blockage severity detection.

# Storage root: /data/uploads/citizen_reports/{year}/{month}/
UPLOADS_ROOT = ROOT_DIR / "data" / "uploads" / "citizen_reports"

# Constraints
MAX_PHOTO_SIZE = 20 * 1024 * 1024  # 20MB
MAX_VIDEO_SIZE = 60 * 1024 * 1024  # 60MB
MAX_VILLAGE_DISTANCE_KM = 25.0     # Radius for nearest village mapping

PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic"}
VIDEO_EXTENSIONS = {".mp4", ".mov"}

PHOTO_MIME_PREFIXES = {"image/jpeg", "image/png", "image/heic", "image/webp"}
VIDEO_MIME_PREFIXES = {"video/mp4", "video/quicktime"}

# Rate limiting: max 5 reports per 15 minutes per IP or phone
RATE_LIMIT_WINDOW_SEC = 900.0  # 15 minutes
MAX_REPORTS_PER_WINDOW = 5
_ip_rate_limits: Dict[str, Deque[float]] = defaultdict(deque)
_phone_rate_limits: Dict[str, Deque[float]] = defaultdict(deque)


# ---------------------------------------------------------------------------
# Rate Limiting & Abuse Protection
# ---------------------------------------------------------------------------

def check_rate_limit(client_ip: Optional[str], phone: Optional[str] = None) -> None:
    """Enforce maximum 5 reports per 15 minutes by IP and phone."""
    now = time.time()
    cutoff = now - RATE_LIMIT_WINDOW_SEC

    # Check client IP
    if client_ip:
        ip_queue = _ip_rate_limits[client_ip]
        while ip_queue and ip_queue[0] < cutoff:
            ip_queue.popleft()
        if len(ip_queue) >= MAX_REPORTS_PER_WINDOW:
            retry_after = int(RATE_LIMIT_WINDOW_SEC - (now - ip_queue[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded: maximum {MAX_REPORTS_PER_WINDOW} reports per 15 minutes. Try again in {retry_after}s.",
            )

    # Check reporter phone
    if phone:
        phone_key = phone.strip()
        phone_queue = _phone_rate_limits[phone_key]
        while phone_queue and phone_queue[0] < cutoff:
            phone_queue.popleft()
        if len(phone_queue) >= MAX_REPORTS_PER_WINDOW:
            retry_after = int(RATE_LIMIT_WINDOW_SEC - (now - phone_queue[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded for phone: maximum {MAX_REPORTS_PER_WINDOW} reports per 15 minutes. Try again in {retry_after}s.",
            )


def record_submission(client_ip: Optional[str], phone: Optional[str] = None) -> None:
    """Record a timestamped report submission for rate limiting."""
    now = time.time()
    if client_ip:
        _ip_rate_limits[client_ip].append(now)
    if phone:
        _phone_rate_limits[phone.strip()].append(now)


def reset_rate_limits() -> None:
    """Helper for testing: clears in-memory rate limiters."""
    _ip_rate_limits.clear()
    _phone_rate_limits.clear()


# ---------------------------------------------------------------------------
# Media Validation & Type Inspection
# ---------------------------------------------------------------------------

def validate_media_type_and_size(filename: str, content_type: Optional[str], file_bytes: bytes) -> str:
    """Validate file type (jpg/png/heic, mp4/mov) and size bounds.
    
    Returns 'photo' or 'video'.
    """
    ext = Path(filename).suffix.lower()
    file_size = len(file_bytes)

    if ext in PHOTO_EXTENSIONS:
        if file_size > MAX_PHOTO_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Photo size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed 20MB.",
            )
        return "photo"

    if ext in VIDEO_EXTENSIONS:
        if file_size > MAX_VIDEO_SIZE:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Video size ({file_size / (1024*1024):.1f}MB) exceeds maximum allowed 60MB.",
            )
        return "video"

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported file type '{ext}'. Allowed types: photos ({', '.join(sorted(PHOTO_EXTENSIONS))}) and videos ({', '.join(sorted(VIDEO_EXTENSIONS))}).",
    )


# ---------------------------------------------------------------------------
# EXIF GPS Extraction & Stripping (Privacy Protection)
# ---------------------------------------------------------------------------

def extract_exif_gps(image: Image.Image) -> Optional[Tuple[float, float]]:
    """Extract (latitude, longitude) from EXIF metadata if present."""
    try:
        exif = image.getexif()
        if not exif:
            return None
        # In Pillow, GPS IFD is tag 34853 (0x8825)
        gps_ifd = exif.get_ifd(0x8825)
        if not gps_ifd:
            return None

        # GPS tags: 1: LatRef, 2: Lat, 3: LonRef, 4: Lon
        lat_ref = gps_ifd.get(1)
        lat = gps_ifd.get(2)
        lon_ref = gps_ifd.get(3)
        lon = gps_ifd.get(4)

        if lat and lon and lat_ref and lon_ref:
            def dms_to_deg(dms):
                d = float(dms[0])
                m = float(dms[1])
                s = float(dms[2])
                return d + (m / 60.0) + (s / 3600.0)

            lat_deg = dms_to_deg(lat)
            if str(lat_ref).upper() == "S":
                lat_deg = -lat_deg

            lon_deg = dms_to_deg(lon)
            if str(lon_ref).upper() == "W":
                lon_deg = -lon_deg

            return lat_deg, lon_deg
    except Exception as exc:
        logger.debug(f"[EXIF] Could not parse GPS metadata: {exc}")
        return None
    return None


def strip_image_exif(image: Image.Image) -> bytes:
    """Re-encode image purely from pixel data, stripping all EXIF and device metadata."""
    # Convert RGBA/P to RGB if JPEG, or keep PNG
    save_format = "PNG" if image.format == "PNG" else "JPEG"
    mode = "RGB" if image.mode not in ("RGB", "L", "RGBA") else image.mode
    if save_format == "JPEG" and mode == "RGBA":
        mode = "RGB"
        converted = image.convert("RGB")
    else:
        converted = image

    clean_image = Image.frombytes(mode, converted.size, converted.tobytes())
    buf = io.BytesIO()
    clean_image.save(buf, format=save_format, quality=90)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Thumbnail Generation
# ---------------------------------------------------------------------------

def generate_photo_thumbnail(image: Image.Image, dest_path: Path, max_dim: int = 300) -> bool:
    """Generate a thumbnail for a photo using Pillow."""
    try:
        thumb = image.copy()
        thumb.thumbnail((max_dim, max_dim), Image.Resampling.LANCZOS)
        if thumb.mode in ("RGBA", "P"):
            thumb = thumb.convert("RGB")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        thumb.save(dest_path, format="JPEG", quality=85)
        return True
    except Exception as exc:
        logger.warning(f"[Thumbnail] Failed to generate photo thumbnail: {exc}")
        return False


def generate_video_thumbnail(video_path: Path, dest_path: Path) -> bool:
    """Generate a video thumbnail (first frame) using ffmpeg if installed."""
    ffmpeg_bin = shutil.which("ffmpeg")
    if not ffmpeg_bin:
        logger.debug("[Thumbnail] ffmpeg not found; skipping video thumbnail gracefully.")
        return False

    try:
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            ffmpeg_bin,
            "-y",
            "-ss", "00:00:00.500",
            "-i", str(video_path),
            "-vframes", "1",
            "-vf", "scale=300:-1",
            str(dest_path),
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=8)
        return result.returncode == 0 and dest_path.exists()
    except Exception as exc:
        logger.warning(f"[Thumbnail] ffmpeg execution error: {exc}")
        return False


# ---------------------------------------------------------------------------
# Reverse Geocoding: Nearest Seeded Village
# ---------------------------------------------------------------------------

def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance in kilometers between two lat/lon pairs."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    return r * 2.0 * math.asin(math.sqrt(max(0.0, a)))


def find_nearest_village(
    lat: float, lon: float, db: Session, max_radius_km: float = MAX_VILLAGE_DISTANCE_KM
) -> Tuple[Optional[str], Optional[str], Optional[float]]:
    """Locate the nearest seeded village within max_radius_km.
    
    Returns (village_id, village_name, distance_km).
    """
    villages = db.query(Village).all()
    if not villages:
        return None, None, None

    best_village: Optional[Village] = None
    min_dist = float("inf")

    for v in villages:
        d = haversine_km(lat, lon, v.lat, v.lon)
        if d < min_dist:
            min_dist = d
            best_village = v

    if best_village and min_dist <= max_radius_km:
        return best_village.id, best_village.name, round(min_dist, 2)

    return None, None, round(min_dist, 2) if best_village else None


# ---------------------------------------------------------------------------
# File Storage Manager
# ---------------------------------------------------------------------------

def get_storage_dir() -> Path:
    """Return /data/uploads/citizen_reports/{year}/{month:02d}/ directory."""
    now = datetime.now(timezone.utc)
    target_dir = UPLOADS_ROOT / str(now.year) / f"{now.month:02d}"
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir
