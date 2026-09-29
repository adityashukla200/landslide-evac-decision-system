"""API endpoints for citizen ground-truth hazard reporting with media uploads,
geotagging, officer verification, and media streaming.
"""

from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from PIL import Image
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.db.models import CitizenReport, Village
from backend.app.core.security import mask_phone_number, get_current_role, UserRole
from backend.app.services.citizen_reports import (
    validate_media_type_and_size,
    extract_exif_gps,
    strip_image_exif,
    generate_photo_thumbnail,
    generate_video_thumbnail,
    find_nearest_village,
    get_storage_dir,
    check_rate_limit,
    record_submission,
    haversine_km,
)

router = APIRouter(prefix="/reports", tags=["Citizen Reports"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ReportStatusUpdate(BaseModel):
    """Payload for an officer to update report verification status."""

    status: str = Field(..., pattern="^(pending|verified|rejected|duplicate)$", description="New status")
    reviewed_by: str = Field("District Officer", min_length=2, max_length=64, description="Officer ID or name")
    notes: Optional[str] = Field(None, max_length=512, description="Audit justification notes")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/citizen", status_code=status.HTTP_201_CREATED)
async def submit_citizen_report(
    request: Request,
    file: UploadFile = File(..., description="Field photo or short video"),
    latitude: Optional[float] = Form(None, ge=-90.0, le=90.0, description="Latitude from client GPS"),
    longitude: Optional[float] = Form(None, ge=-180.0, le=180.0, description="Longitude from client GPS"),
    accuracy_meters: Optional[float] = Form(None, ge=0.0, description="GPS fix accuracy in meters"),
    reported_flood: bool = Form(True, description="True for flood/landslide, False for all-clear/false alarm"),
    caption: Optional[str] = Form(None, max_length=1000, description="Observer notes or landmarks"),
    reporter_phone: Optional[str] = Form(None, max_length=32, description="Contact phone for verification"),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Submit a geotagged citizen hazard observation with photo or video."""
    client_ip = request.client.host if request.client else "127.0.0.1"

    # 1. Enforce rate limiting (max 5 per 15 min)
    check_rate_limit(client_ip, reporter_phone)

    # 2. Read media file bytes
    file_bytes = await file.read()
    filename = file.filename or "upload.jpg"
    content_type = file.content_type

    # 3. Validate media type and size
    media_type = validate_media_type_and_size(filename, content_type, file_bytes)

    # 4. Handle EXIF extraction and stripping for photos
    final_lat = latitude
    final_lon = longitude
    saved_bytes = file_bytes
    thumb_path: Optional[Path] = None

    report_id = f"CR_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid.uuid4().hex[:8]}"
    storage_dir = get_storage_dir()
    ext = Path(filename).suffix.lower()
    if not ext:
        ext = ".jpg" if media_type == "photo" else ".mp4"

    dest_file = storage_dir / f"{report_id}{ext}"
    dest_thumb = storage_dir / f"{report_id}_thumb.jpg"

    if media_type == "photo":
        try:
            image = Image.open(io.BytesIO(file_bytes))
            # If lat/lon not explicitly provided by client, try extracting from EXIF
            if final_lat is None or final_lon is None:
                exif_coords = extract_exif_gps(image)
                if exif_coords:
                    final_lat, final_lon = exif_coords

            # Strip EXIF for privacy before saving
            saved_bytes = strip_image_exif(image)

            # Generate thumbnail
            if generate_photo_thumbnail(image, dest_thumb):
                thumb_path = dest_thumb
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid or corrupted image file: {exc}",
            )
    else:
        # Video: save directly
        saved_bytes = file_bytes

    # 5. Coordinate requirement check: reject if coordinates still missing
    if final_lat is None or final_lon is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Geographic coordinates required. Please supply latitude/longitude or upload a photo with EXIF GPS metadata.",
        )

    # 6. Save media file to disk (under /data/uploads/citizen_reports/{year}/{month}/)
    with open(dest_file, "wb") as f:
        f.write(saved_bytes)

    # For videos, generate thumbnail if ffmpeg is available
    if media_type == "video":
        if generate_video_thumbnail(dest_file, dest_thumb):
            thumb_path = dest_thumb

    # 7. Reverse-map to nearest seeded village
    village_id, village_name, distance_km = find_nearest_village(final_lat, final_lon, db)

    # 8. Insert record in citizen_reports table
    report = CitizenReport(
        id=report_id,
        village_id=village_id,
        latitude=final_lat,
        longitude=final_lon,
        accuracy_meters=accuracy_meters,
        media_type=media_type,
        file_path=str(dest_file.resolve()),
        thumbnail_path=str(thumb_path.resolve()) if thumb_path else None,
        caption=caption,
        reported_flood=reported_flood,
        reporter_phone=reporter_phone,
        status="pending",
        created_at=datetime.now(timezone.utc),
        audit_log=[
            {
                "action": "submitted",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "client_ip": client_ip,
            }
        ],
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    # 9. Record rate limit timestamp
    record_submission(client_ip, reporter_phone)

    return {
        "status": "success",
        "message": "Report submitted successfully. Thank you for contributing ground truth.",
        "report_id": report.id,
        "village_id": report.village_id,
        "village_name": village_name,
        "distance_from_village_km": distance_km,
        "latitude": report.latitude,
        "longitude": report.longitude,
        "media_type": report.media_type,
        "media_url": f"/api/v1/reports/{report.id}/media",
        "thumbnail_url": f"/api/v1/reports/{report.id}/thumbnail" if report.thumbnail_path else None,
        "reported_flood": report.reported_flood,
        "review_status": report.status,
        "created_at": report.created_at.isoformat(),
    }


@router.get("", response_model=List[Dict[str, Any]])
def list_citizen_reports(
    village_id: Optional[str] = Query(None, description="Filter by mapped village ID"),
    status_filter: Optional[str] = Query(None, alias="status", description="Filter: pending, verified, rejected, duplicate"),
    since: Optional[str] = Query(None, description="ISO datetime string to filter reports created on or after"),
    reported_flood: Optional[bool] = Query(None, description="Filter by flood vs no-flood reports"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> List[Dict[str, Any]]:
    """Query ground-truth hazard reports for the dashboard and risk maps."""
    query = db.query(CitizenReport)

    if village_id:
        query = query.filter(CitizenReport.village_id == village_id)

    if status_filter:
        query = query.filter(CitizenReport.status == status_filter.lower())

    if reported_flood is not None:
        query = query.filter(CitizenReport.reported_flood == reported_flood)

    if since:
        try:
            since_dt = datetime.fromisoformat(since.replace("Z", "+00:00"))
            query = query.filter(CitizenReport.created_at >= since_dt)
        except Exception:
            pass

    records = query.order_by(CitizenReport.created_at.desc()).limit(limit).all()

    # Pre-fetch villages for distance and name mapping
    village_map = {v.id: v for v in db.query(Village).all()}

    output = []
    for r in records:
        v = village_map.get(r.village_id) if r.village_id else None
        v_name = v.name if v else None
        dist_km = round(haversine_km(r.latitude, r.longitude, v.lat, v.lon), 2) if v else None

        output.append({
            "id": r.id,
            "village_id": r.village_id,
            "village_name": v_name,
            "distance_from_village_km": dist_km,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "accuracy_meters": r.accuracy_meters,
            "media_type": r.media_type,
            "media_url": f"/api/v1/reports/{r.id}/media",
            "thumbnail_url": f"/api/v1/reports/{r.id}/thumbnail" if r.thumbnail_path else f"/api/v1/reports/{r.id}/media",
            "caption": r.caption,
            "reported_flood": r.reported_flood,
            "reporter_phone": mask_phone_number(r.reporter_phone),
            "status": r.status,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
            "audit_log": r.audit_log or [],
        })

    return output


@router.get("/{report_id}/media")
def stream_report_media(report_id: str, db: Session = Depends(get_db)):
    """Stream stored photo or video file."""
    report = db.query(CitizenReport).filter(CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )

    file_path = Path(report.file_path)
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Media file is missing on storage.",
        )

    media_type_header = "image/jpeg"
    ext = file_path.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        media_type_header = "image/jpeg"
    elif ext == ".png":
        media_type_header = "image/png"
    elif ext == ".mp4":
        media_type_header = "video/mp4"
    elif ext == ".mov":
        media_type_header = "video/quicktime"

    return FileResponse(path=file_path, media_type=media_type_header, filename=file_path.name)


@router.get("/{report_id}/thumbnail")
def stream_report_thumbnail(report_id: str, db: Session = Depends(get_db)):
    """Stream photo or video preview thumbnail."""
    report = db.query(CitizenReport).filter(CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )

    # Use thumbnail if exists, otherwise fallback to main file for photos
    target_path = Path(report.thumbnail_path) if report.thumbnail_path else Path(report.file_path)
    if not target_path.exists():
        target_path = Path(report.file_path)

    if not target_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Thumbnail file not found.",
        )

    return FileResponse(path=target_path, media_type="image/jpeg", filename=target_path.name)


@router.put("/{report_id}/status")
def update_report_status(
    report_id: str,
    update_in: ReportStatusUpdate,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """Officer verification endpoint: marks report as verified, rejected, or duplicate with audit log."""
    report = db.query(CitizenReport).filter(CitizenReport.id == report_id).first()
    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report '{report_id}' not found.",
        )

    old_status = report.status
    now_utc = datetime.now(timezone.utc)

    report.status = update_in.status.lower()
    report.reviewed_by = update_in.reviewed_by
    report.reviewed_at = now_utc

    # Append to audit log
    audit_entry = {
        "action": "status_change",
        "old_status": old_status,
        "new_status": report.status,
        "changed_by": update_in.reviewed_by,
        "notes": update_in.notes,
        "timestamp": now_utc.isoformat(),
    }
    current_audit = list(report.audit_log or [])
    current_audit.append(audit_entry)
    report.audit_log = current_audit

    db.commit()
    db.refresh(report)

    return {
        "status": "success",
        "report_id": report.id,
        "new_status": report.status,
        "reviewed_by": report.reviewed_by,
        "reviewed_at": report.reviewed_at.isoformat(),
        "audit_log": report.audit_log,
    }
