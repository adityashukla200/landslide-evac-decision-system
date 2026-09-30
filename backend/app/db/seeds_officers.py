"""Seed demo officer accounts for the Uttarkashi pilot."""

from datetime import datetime, timezone
from sqlalchemy.orm import Session

from backend.app.db.session import SessionLocal, engine
from backend.app.db.models import Base, Officer
from backend.app.core.security import hash_password


DEMO_OFFICERS = [
    {
        "id": "OFF_DDMO_UTK_01",
        "name": "Dr. Rajesh Sharma",
        "district": "Uttarkashi",
        "email": "ddmo.uttarkashi@uk.gov.in",
        "phone": "+919412011001",
        "role": "admin",
        "designation": "District Disaster Management Officer (DDMO)",
        "password": "Uttarkashi@2026",
    },
    {
        "id": "OFF_NDRF_UTK_02",
        "name": "Maj. Vikram Negi",
        "district": "Uttarkashi",
        "email": "ndrf.uttarkashi@gov.in",
        "phone": "+919412022002",
        "role": "officer",
        "designation": "NDRF 15th Battalion Commander",
        "password": "NDRF#Rescue2026",
    },
    {
        "id": "OFF_BDO_BHT_03",
        "name": "Pooja Rawat",
        "district": "Uttarkashi",
        "email": "bdo.bhatwari@uk.gov.in",
        "phone": "+919412033003",
        "role": "officer",
        "designation": "Block Development Officer (BDO), Bhatwari",
        "password": "Bhatwari@2026",
    },
]


def seed_officers(db: Session = None) -> int:
    """Seed demo officer accounts if they do not already exist."""
    close_db = False
    if db is None:
        Base.metadata.create_all(bind=engine)
        db = SessionLocal()
        close_db = True

    try:
        count = 0
        for off_data in DEMO_OFFICERS:
            existing = db.query(Officer).filter(
                (Officer.id == off_data["id"]) | (Officer.email == off_data["email"])
            ).first()
            if not existing:
                officer = Officer(
                    id=off_data["id"],
                    name=off_data["name"],
                    district=off_data["district"],
                    email=off_data["email"],
                    phone=off_data["phone"],
                    role=off_data["role"],
                    designation=off_data["designation"],
                    password_hash=hash_password(off_data["password"]),
                    created_at=datetime.now(timezone.utc),
                    is_active=True,
                )
                db.add(officer)
                count += 1
            else:
                # Update password hash to match demo password in case DB had previous state
                existing.password_hash = hash_password(off_data["password"])
                existing.is_active = True

        db.commit()
        return count
    finally:
        if close_db:
            db.close()


if __name__ == "__main__":
    added = seed_officers()
    print(f"Seeded {added} demo officers successfully.")
