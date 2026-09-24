"""Floats and profiles endpoints."""

from fastapi import APIRouter, HTTPException
from typing import List
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.schema import ArgoFloat, ArgoProfile, ProfileLevel
from app.schemas.forecast import FloatSummary, ArgoProfile as ArgoProfileSchema, ArgoMeasurement

router = APIRouter()


def get_db() -> Session:
    """Get database session."""
    db = SessionLocal()
    try:
        return db
    finally:
        db.close()


@router.get("/floats", response_model=List[FloatSummary])
async def get_floats():
    """
    Get list of all available Argo floats with their cycles.
    
    Returns catalog of active floats in the Arabian Sea with base coordinates and cycle lists.
    """
    db = get_db()
    try:
        floats = db.query(ArgoFloat).all()
        
        result = []
        for f in floats:
            # Get cycles for this float
            profiles = db.query(ArgoProfile).filter(ArgoProfile.wmo_id == f.wmo_id).all()
            cycles = sorted([p.cycle_number for p in profiles])
            
            default_cycle = max(cycles) if cycles else 0
            
            result.append(FloatSummary(
                wmo_id=f.wmo_id,
                name=f.name,
                baseLat=f.base_lat,
                baseLon=f.base_lon,
                cycles=cycles,
                defaultCycle=default_cycle
            ))
        
        return result
    finally:
        db.close()


@router.get("/profiles/{wmoId}", response_model=list)
async def get_profiles(wmoId: str):
    """
    Get all historical profiles for a given float ID.
    
    Returns all historical vertical profile cycles for a float, sorted by cycle number.
    """
    db = get_db()
    try:
        profiles = db.query(ArgoProfile).filter(
            ArgoProfile.wmo_id == wmoId
        ).order_by(ArgoProfile.cycle_number.asc()).all()
        
        if not profiles:
            raise HTTPException(status_code=404, detail=f"Float {wmoId} not found")
        
        result = []
        for p in profiles:
            # Get measurements for this profile
            levels = db.query(ProfileLevel).filter(
                ProfileLevel.profile_id == p.profile_id
            ).order_by(ProfileLevel.depth_dbar.asc()).all()
            
            measurements = [
                {
                    "depth_dbar": l.depth_dbar,
                    "temperature": l.temperature,
                    "salinity": l.salinity,
                    "qc_temperature": 1,
                    "qc_salinity": 1
                }
                for l in levels
            ]
            
            result.append({
                "profile_id": p.profile_id,
                "wmo_id": p.wmo_id,
                "float_name": f"Argo-{p.wmo_id} (North Arabian Sea)",
                "platform_type": "PROVOR_CTS4",
                "cycle_number": p.cycle_number,
                "date": p.date.isoformat() if p.date else "",
                "latitude": p.latitude,
                "longitude": p.longitude,
                "sea_region": "Arabian Sea (Northern Indian Ocean)",
                "data_mode": "D",
                "qc_status": p.qc_status,
                "raw_netcdf_source": p.raw_netcdf_source,
                "gdac_archive_path": p.gdac_archive_path,
                "measurements": measurements
            })
        
        return result
    finally:
        db.close()