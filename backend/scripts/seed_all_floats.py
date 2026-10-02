#!/usr/bin/env python
"""
Seed database with ALL floats from the canonical CSV.

Reads from backend/data/processed/argo_floats_canonical.csv and inserts
ArgoFloat, ArgoProfile, and ProfileLevel records for every float/cycle found.
"""
import sys
import csv
from pathlib import Path
from datetime import datetime
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal, init_db
from app.models.schema import ArgoFloat, ArgoProfile, ProfileLevel

# Standard depth grid
STANDARD_DEPTHS = [5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]

# Float metadata (names and regions)
FLOAT_NAMES = {
    "3902114": "Float 3902114 (Northern Arabian Sea / Gulf of Oman)",
    "2903334": "Float 2903334 (Central Arabian Sea Basin)",
    "1902442": "Float 1902442 (Eastern Arabian Sea / Indian West Shelf)",
    "2902789": "Float 2902789 (Southwestern Upwelling Corridor)",
}

def get_float_name(wmo):
    if wmo in FLOAT_NAMES:
        return FLOAT_NAMES[wmo]
    return f"Float {wmo} (Arabian Sea)"


def main():
    csv_path = Path(__file__).parent.parent / "data" / "processed" / "argo_floats_canonical.csv"
    if not csv_path.exists():
        print(f"ERROR: CSV not found at {csv_path}")
        sys.exit(1)

    init_db()
    db = SessionLocal()

    try:
        # Read all rows from CSV
        rows = []
        with open(csv_path, "r") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)

        print(f"Read {len(rows)} rows from CSV")

        # Group by WMO
        by_wmo = defaultdict(list)
        for row in rows:
            by_wmo[row["wmo"]].append(row)

        print(f"Found {len(by_wmo)} unique floats")

        total_new_floats = 0
        total_new_profiles = 0
        total_new_levels = 0

        for wmo, wmo_rows in sorted(by_wmo.items()):
            # Check if float already exists
            existing = db.query(ArgoFloat).filter(ArgoFloat.wmo_id == wmo).first()
            if not existing:
                # Use first row for base coordinates
                first_row = wmo_rows[0]
                argo_float = ArgoFloat(
                    wmo_id=wmo,
                    name=get_float_name(wmo),
                    base_lat=float(first_row["latitude"]),
                    base_lon=float(first_row["longitude"]),
                    institution="INCOIS / Argo GDAC",
                    status="ACTIVE",
                    created_at=datetime.utcnow()
                )
                db.add(argo_float)
                db.flush()
                total_new_floats += 1
                print(f"  Created float: {wmo}")

            # Process each cycle
            for row in wmo_rows:
                cycle = int(row["cycle"])
                profile_id = f"ARGO_{wmo}_CYC{cycle:03d}"

                # Check if profile already exists
                existing_p = db.query(ArgoProfile).filter(
                    ArgoProfile.profile_id == profile_id
                ).first()
                if existing_p:
                    continue

                # Parse date
                try:
                    date_val = datetime.strptime(row["date"], "%Y-%m-%d").date()
                except Exception:
                    date_val = datetime.utcnow().date()

                profile = ArgoProfile(
                    profile_id=profile_id,
                    wmo_id=wmo,
                    cycle_number=cycle,
                    date=date_val,
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    qc_status="QC_PASS_FLAG_1" if row.get("data_mode") == "D" else "QC_PASS_FLAG_2",
                    raw_netcdf_source=f"D{wmo}_{cycle:03d}.nc",
                    gdac_archive_path=f"dac/coriolis/{wmo}/profiles/D{wmo}_{cycle:03d}.nc",
                    created_at=datetime.utcnow()
                )
                db.add(profile)
                db.flush()
                total_new_profiles += 1

                # Add profile levels for each standard depth
                for depth in STANDARD_DEPTHS:
                    temp_key = f"temp_{depth}"
                    sal_key = f"sal_{depth}"
                    sigma_key = f"sigma_{depth}"

                    temp = float(row.get(temp_key, 0))
                    sal = float(row.get(sal_key, 0))
                    sigma = float(row.get(sigma_key, 0))

                    level = ProfileLevel(
                        profile_id=profile_id,
                        depth_dbar=float(depth),
                        temperature=temp,
                        salinity=sal,
                        potential_density=sigma
                    )
                    db.add(level)
                    total_new_levels += 1

            db.commit()

        print(f"\nSeeding complete!")
        print(f"  New floats: {total_new_floats}")
        print(f"  New profiles: {total_new_profiles}")
        print(f"  New levels: {total_new_levels}")

        # Verify
        float_count = db.query(ArgoFloat).count()
        profile_count = db.query(ArgoProfile).count()
        level_count = db.query(ProfileLevel).count()
        print(f"\nDatabase totals:")
        print(f"  Floats: {float_count}")
        print(f"  Profiles: {profile_count}")
        print(f"  Levels: {level_count}")

    except Exception as e:
        db.rollback()
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
