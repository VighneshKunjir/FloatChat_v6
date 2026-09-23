#!/usr/bin/env python
"""
FloatChat Database Seeding Script

Ingests the self-contained offline dataset (backend/data/seed_reference_profiles.json)
containing historical profile cycles and standardized 16 depth levels for the 4
operational Arabian Sea reference floats (3902114, 2903334, 1902442, 2902789).

Ensures zero network/FTP failures for local development.
"""
import json
import argparse
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

# Add backend to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.session import SessionLocal, init_db
from app.models.schema import ArgoFloat, ArgoProfile, ProfileLevel


def load_seed_data(json_path: Path) -> Dict[str, Any]:
    """Load the seed reference profiles JSON file."""
    with open(json_path, "r") as f:
        return json.load(f)


def seed_database(db_url: str = None) -> None:
    """Seed the database with reference profile data."""
    # Override DATABASE_URL if provided
    if db_url:
        import os
        os.environ["DATABASE_URL"] = db_url
    
    # Initialize database tables
    init_db()
    
    # Get session
    db = SessionLocal()
    
    try:
        # Load seed data
        json_path = Path(__file__).parent.parent / "data" / "seed_reference_profiles.json"
        print(f"Loading seed data from: {json_path}")
        data = load_seed_data(json_path)
        
        floats_data = data.get("floats", [])
        print(f"Found {len(floats_data)} floats to seed")
        
        total_profiles = 0
        total_levels = 0
        
        for float_data in floats_data:
            wmo_id = float_data["wmo_id"]
            
            # Check if float already exists
            existing_float = db.query(ArgoFloat).filter(ArgoFloat.wmo_id == wmo_id).first()
            if existing_float:
                print(f"Float {wmo_id} already exists, skipping...")
                continue
            
            # Create ArgoFloat
            argo_float = ArgoFloat(
                wmo_id=wmo_id,
                name=float_data["name"],
                base_lat=float_data["baseLat"],
                base_lon=float_data["baseLon"],
                institution="INCOIS / Argo GDAC",
                status="ACTIVE",
                created_at=datetime.utcnow()
            )
            db.add(argo_float)
            db.flush()
            
            print(f"Created float: {wmo_id} - {float_data['name']}")
            
            # Process profiles
            profiles_data = float_data.get("profiles", [])
            for profile_data in profiles_data:
                profile_id = profile_data["profile_id"]
                
                # Check if profile already exists
                existing_profile = db.query(ArgoProfile).filter(
                    ArgoProfile.profile_id == profile_id
                ).first()
                if existing_profile:
                    print(f"  Profile {profile_id} already exists, skipping...")
                    continue
                
                argo_profile = ArgoProfile(
                    profile_id=profile_id,
                    wmo_id=wmo_id,
                    cycle_number=profile_data["cycle_number"],
                    date=datetime.strptime(profile_data["date"], "%Y-%m-%d").date(),
                    latitude=profile_data["latitude"],
                    longitude=profile_data["longitude"],
                    qc_status=profile_data.get("qc_status", "QC_PASS_FLAG_1"),
                    raw_netcdf_source=profile_data.get("raw_netcdf_source", ""),
                    gdac_archive_path=profile_data.get("gdac_archive_path", ""),
                    created_at=datetime.utcnow()
                )
                db.add(argo_profile)
                db.flush()
                
                total_profiles += 1
                
                # Process levels
                levels_data = profile_data.get("levels", [])
                for level_data in levels_data:
                    depth_dbar = level_data["depth_dbar"]
                    
                    # Check if level already exists
                    existing_level = db.query(ProfileLevel).filter(
                        ProfileLevel.profile_id == profile_id,
                        ProfileLevel.depth_dbar == depth_dbar
                    ).first()
                    if existing_level:
                        continue
                    
                    profile_level = ProfileLevel(
                        profile_id=profile_id,
                        depth_dbar=depth_dbar,
                        temperature=level_data["temperature"],
                        salinity=level_data["salinity"],
                        potential_density=level_data.get("potential_density", 0.0)  # Will be computed by physics engine
                    )
                    db.add(profile_level)
                    total_levels += 1
            
            # Commit after each float to avoid memory issues
            db.commit()
            print(f"  Committed {len(profiles_data)} profiles for {wmo_id}")
        
        print(f"\nSeeding complete!")
        print(f"Total floats: {len(floats_data)}")
        print(f"Total profiles: {total_profiles}")
        print(f"Total level measurements: {total_levels}")
        
        # Verify
        float_count = db.query(ArgoFloat).count()
        profile_count = db.query(ArgoProfile).count()
        level_count = db.query(ProfileLevel).count()
        print(f"\nVerification:")
        print(f"  Floats in DB: {float_count}")
        print(f"  Profiles in DB: {profile_count}")
        print(f"  Levels in DB: {level_count}")
        
    except Exception as e:
        db.rollback()
        print(f"Error during seeding: {e}", file=sys.stderr)
        raise
    finally:
        db.close()


def main():
    parser = argparse.ArgumentParser(description="Seed FloatChat database with Argo reference profiles")
    parser.add_argument(
        "--db-url",
        type=str,
        default=None,
        help="Database URL (e.g., sqlite:///./backend/data/floatchat.db or postgresql://...)"
    )
    args = parser.parse_args()
    
    print("FloatChat Database Seeding Script")
    print("=" * 50)
    
    seed_database(args.db_url)
    
    print("\nDone!")


if __name__ == "__main__":
    main()