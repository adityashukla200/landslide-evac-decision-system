"""Seed script generating 25 realistic synthetic villages for Uttarkashi district (Uttarakhand).

Includes topography, coordinates, population, sensors, safe shelters, evacuation routes,
and vulnerable recipient registries for pilot disaster simulation.
"""

import json
import random
from datetime import datetime, timezone
from typing import List, Dict, Any
import sys
from pathlib import Path
from shapely.geometry import box, Point, mapping

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.core.config import settings
from backend.app.db.session import SessionLocal, engine, Base
from backend.app.db.models import (
    Village,
    VillageThreshold,
    Sensor,
    Shelter,
    Route,
    Recipient,
)

# Realistic pilot villages in Uttarkashi district, Uttarakhand (Bhagirathi, Yamuna & Tons valleys)
UTTARKASHI_VILLAGES: List[Dict[str, Any]] = [
    {"name": "Harsil", "lat": 31.0367, "lon": 78.7378, "elevation": 2745.0, "population": 1250, "valley": "Bhagirathi"},
    {"name": "Dharali", "lat": 31.0450, "lon": 78.7520, "elevation": 2680.0, "population": 840, "valley": "Bhagirathi"},
    {"name": "Mukhba", "lat": 31.0310, "lon": 78.7450, "elevation": 2620.0, "population": 620, "valley": "Bhagirathi"},
    {"name": "Jhala", "lat": 31.0250, "lon": 78.7050, "elevation": 2450.0, "population": 780, "valley": "Bhagirathi"},
    {"name": "Sukhi", "lat": 30.9980, "lon": 78.6850, "elevation": 2350.0, "population": 910, "valley": "Bhagirathi"},
    {"name": "Gangnani", "lat": 30.9080, "lon": 78.6420, "elevation": 1855.0, "population": 1120, "valley": "Bhagirathi"},
    {"name": "Bhatwari", "lat": 30.8140, "lon": 78.6180, "elevation": 1218.0, "population": 2840, "valley": "Bhagirathi"},
    {"name": "Maneri", "lat": 30.7620, "lon": 78.5340, "elevation": 1290.0, "population": 1950, "valley": "Bhagirathi"},
    {"name": "Netala", "lat": 30.7510, "lon": 78.4980, "elevation": 1210.0, "population": 1420, "valley": "Bhagirathi"},
    {"name": "Uttarkashi Town", "lat": 30.7268, "lon": 78.4354, "elevation": 1158.0, "population": 4800, "valley": "Bhagirathi"},
    {"name": "Joshiyara", "lat": 30.7180, "lon": 78.4410, "elevation": 1150.0, "population": 3600, "valley": "Bhagirathi"},
    {"name": "Matli", "lat": 30.6980, "lon": 78.4050, "elevation": 1140.0, "population": 1850, "valley": "Bhagirathi"},
    {"name": "Dunda", "lat": 30.6480, "lon": 78.3420, "elevation": 1050.0, "population": 2200, "valley": "Bhagirathi"},
    {"name": "Chinyalisaur", "lat": 30.5620, "lon": 78.3150, "elevation": 850.0, "population": 4100, "valley": "Bhagirathi"},
    {"name": "Barkot", "lat": 30.8100, "lon": 78.2080, "elevation": 1220.0, "population": 3900, "valley": "Yamuna"},
    {"name": "Naugaon", "lat": 30.7850, "lon": 78.1420, "elevation": 1180.0, "population": 2150, "valley": "Yamuna"},
    {"name": "Purola", "lat": 30.8830, "lon": 78.0820, "elevation": 1524.0, "population": 3200, "valley": "Kamal"},
    {"name": "Mori", "lat": 31.0180, "lon": 78.0420, "elevation": 1150.0, "population": 1650, "valley": "Tons"},
    {"name": "Netwar", "lat": 31.0480, "lon": 78.1180, "elevation": 1410.0, "population": 980, "valley": "Tons"},
    {"name": "Sankri", "lat": 31.0790, "lon": 78.1810, "elevation": 1950.0, "population": 870, "valley": "Supa"},
    {"name": "Taluka", "lat": 31.0920, "lon": 78.2580, "elevation": 2120.0, "population": 540, "valley": "Supa"},
    {"name": "Osla", "lat": 31.1350, "lon": 78.3540, "elevation": 2600.0, "population": 480, "valley": "Supa"},
    {"name": "Jakhol", "lat": 31.1120, "lon": 78.1650, "elevation": 2200.0, "population": 920, "valley": "Tons"},
    {"name": "Singot", "lat": 30.7420, "lon": 78.3750, "elevation": 1380.0, "population": 760, "valley": "Bhagirathi"},
    {"name": "Athali", "lat": 30.6820, "lon": 78.4210, "elevation": 1450.0, "population": 830, "valley": "Bhagirathi"},
]


def seed_database() -> None:
    """Populate database with 25 synthetic Uttarkashi pilot villages and related entities."""
    random.seed(42)  # Deterministic seed for reproducible testing
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Clear existing seed data
        db.query(VillageThreshold).delete()
        db.query(Route).delete()
        db.query(Shelter).delete()
        db.query(Recipient).delete()
        db.query(Sensor).delete()
        db.query(Village).delete()
        db.commit()

        print(f"[*] Seeding 25 pilot villages in Uttarkashi district (Mode: {'Postgres' if settings.is_postgres else 'SQLite'})...")

        for idx, item in enumerate(UTTARKASHI_VILLAGES, start=1):
            village_id = f"VIL_UTK_{idx:02d}"
            lat, lon = item["lat"], item["lon"]

            # Bounding box polygon for village boundary (~600m across)
            delta = 0.003
            poly = box(lon - delta, lat - delta, lon + delta, lat + delta)
            geom_str = json.dumps(mapping(poly))

            village = Village(
                id=village_id,
                name=item["name"],
                district="Uttarkashi",
                geometry=geom_str,
                population=item["population"],
                lat=lat,
                lon=lon,
                elevation=item["elevation"],
            )
            db.add(village)

            # 1. Sensors: Rainfall gauge + Soil moisture sensor for each village
            rain_sensor = Sensor(
                id=f"SNS_RAIN_{village_id}",
                village_id=village_id,
                type="rainfall",
                status="active",
                last_seen=datetime.now(timezone.utc),
            )
            soil_sensor = Sensor(
                id=f"SNS_SOIL_{village_id}",
                village_id=village_id,
                type="soil_moisture",
                status="active",
                last_seen=datetime.now(timezone.utc),
            )
            db.add(rain_sensor)
            db.add(soil_sensor)

            # Add river gauge for lower valley / riverside settlements
            if item["elevation"] < 1500.0:
                river_sensor = Sensor(
                    id=f"SNS_RIVER_{village_id}",
                    village_id=village_id,
                    type="river_gauge",
                    status="active",
                    last_seen=datetime.now(timezone.utc),
                )
                db.add(river_sensor)

            # 2. Designated Safe High-Ground Shelter
            shelter_id = f"SHL_{village_id}"
            shelter_lat = lat + 0.004  # Positioned on higher ridge
            shelter_lon = lon + 0.002
            shelter_pt = Point(shelter_lon, shelter_lat)
            shelter = Shelter(
                id=shelter_id,
                name=f"{item['name']} High-Ground Relief Shelter",
                geometry=json.dumps(mapping(shelter_pt)),
                capacity=max(250, int(item["population"] * 0.4)),
                village_id=village_id,
            )
            db.add(shelter)

            # 3. Safe Evacuation Route from village center to shelter
            walk_minutes = round(random.uniform(10.0, 28.0), 1)
            length_m = round(walk_minutes * 65.0, 1)  # ~4 km/h uphill walking pace
            cut_risk = round(random.uniform(0.02, 0.20), 2)

            route = Route(
                id=f"RTE_{village_id}_TO_{shelter_id}",
                from_village=village_id,
                to_shelter=shelter_id,
                length_m=length_m,
                est_walk_minutes=walk_minutes,
                cut_risk=cut_risk,
            )
            db.add(route)

            # 4. Recipients: Village Pradhan (volunteer coordinator) + 2 residents
            volunteer_id = f"RCP_{village_id}_VOL"
            volunteer = Recipient(
                id=volunteer_id,
                village_id=village_id,
                phone=f"+9198765{idx:02d}001",
                language="hi",
                vulnerable_flag=False,
                volunteer_id=None,
            )
            db.add(volunteer)

            # Vulnerable resident (elderly/mobility-impaired) assigned to volunteer
            vulnerable_resident = Recipient(
                id=f"RCP_{village_id}_VUL",
                village_id=village_id,
                phone=f"+9198765{idx:02d}002",
                language="hi",
                vulnerable_flag=True,
                volunteer_id=volunteer_id,
            )
            db.add(vulnerable_resident)

        db.commit()

        # Seed initial Bayes-optimal thresholds for all villages
        from ml.decision.thresholds import init_village_thresholds
        init_village_thresholds(db, force_recompute=True)

        print(f"[+] Successfully seeded {len(UTTARKASHI_VILLAGES)} villages with shelters, routes, sensors, recipients, and operational thresholds.")
    except Exception as exc:
        db.rollback()
        print(f"[!] Error seeding database: {exc}")
        raise exc
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
