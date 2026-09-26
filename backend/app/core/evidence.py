"""
Evidence-Link Cosine Provenance Matcher

Implements composite similarity scoring combining:
- Vector cosine similarity (75%) on T/S profiles
- Haversine spatial proximity (25%) on lat/lon

Matches query profiles against historical database for GDAC NetCDF citations.
"""
import numpy as np
from typing import List, Dict, Tuple, Optional
from sqlalchemy.orm import Session
from math import radians, sin, cos, sqrt, atan2

from app.models.schema import ArgoProfile, ProfileLevel


# Standard depths for vector comparison
STANDARD_DEPTHS = np.array([5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000], dtype=float)

# Composite weights
COSINE_WEIGHT = 0.75
SPATIAL_WEIGHT = 0.25

# Earth radius in km
EARTH_RADIUS_KM = 6371.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Compute great-circle distance between two points using Haversine formula.
    
    Returns distance in kilometers.
    """
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return EARTH_RADIUS_KM * c


def cosine_similarity(vec1: np.ndarray, vec2: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.
    
    Returns value in [0, 1], where 1 = identical direction.
    """
    vec1 = np.asarray(vec1, dtype=float)
    vec2 = np.asarray(vec2, dtype=float)
    
    # Handle NaN values
    valid = ~(np.isnan(vec1) | np.isnan(vec2))
    if not np.any(valid):
        return 0.0
    
    v1 = vec1[valid]
    v2 = vec2[valid]
    
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    
    if norm1 == 0 or norm2 == 0:
        return 0.0
    
    return float(np.dot(v1, v2) / (norm1 * norm2))


def build_profile_vector(profile_id: str, db: Session) -> Tuple[np.ndarray, Dict]:
    """
    Build concatenated T+S vector for a profile from database.
    
    Returns (vector_32, metadata_dict) or (None, {}) if not found.
    """
    levels = db.query(ProfileLevel).filter(
        ProfileLevel.profile_id == profile_id
    ).order_by(ProfileLevel.depth_dbar).all()
    
    if not levels or len(levels) != 16:
        return None, {}
    
    temps = np.array([l.temperature for l in levels], dtype=float)
    sals = np.array([l.salinity for l in levels], dtype=float)
    
    # Concatenate T + S = 32 features
    vector = np.concatenate([temps, sals])
    
    # Get profile metadata
    profile = db.query(ArgoProfile).filter(
        ArgoProfile.profile_id == profile_id
    ).first()
    
    meta = {}
    if profile:
        meta = {
            'wmo_id': profile.wmo_id,
            'cycle': profile.cycle_number,
            'date': str(profile.date),
            'latitude': profile.latitude,
            'longitude': profile.longitude,
            'raw_netcdf_source': profile.raw_netcdf_source,
            'gdac_archive_path': profile.gdac_archive_path,
            'qc_status': profile.qc_status
        }
    
    return vector, meta


def spatial_similarity(lat1: float, lon1: float, lat2: float, lon2: float,
                       max_dist_km: float = 500.0) -> float:
    """
    Compute spatial proximity score from Haversine distance.
    
    Returns similarity in [0, 1], where 1 = same location.
    Exponential decay with distance.
    """
    dist = haversine_distance(lat1, lon1, lat2, lon2)
    
    if dist >= max_dist_km:
        return 0.0
    
    # Exponential decay: similarity = exp(-dist / scale)
    # scale = max_dist / 3 gives ~5% similarity at max_dist
    scale = max_dist_km / 3.0
    return float(np.exp(-dist / scale))


def composite_similarity(query_vec: np.ndarray, query_lat: float, query_lon: float,
                          cand_vec: np.ndarray, cand_lat: float, cand_lon: float,
                          max_dist_km: float = 500.0) -> float:
    """
    Compute composite similarity score.
    
    Score = 0.75 * cosine_similarity + 0.25 * spatial_similarity
    
    Returns value in [0, 1].
    """
    cos_sim = cosine_similarity(query_vec, cand_vec)
    spat_sim = spatial_similarity(query_lat, query_lon, cand_lat, cand_lon, max_dist_km)
    
    return COSINE_WEIGHT * cos_sim + SPATIAL_WEIGHT * spat_sim


def find_analogues(wmo_id: str, cycle: int, db: Session,
                   n_results: int = 3,
                   max_distance_km: float = 500.0,
                   min_cosine: float = 0.5,
                   exclude_same_float: bool = True) -> List[Dict]:
    """
    Find top N historical profiles matching the query profile.
    
    Args:
        wmo_id: Target float WMO ID
        cycle: Target cycle number
        db: Database session
        n_results: Number of top matches to return
        max_distance_km: Maximum spatial distance for candidates
        min_cosine: Minimum cosine similarity threshold
        exclude_same_float: Exclude profiles from same float (avoid self-match)
    
    Returns:
        List of dicts with match metadata and similarity scores
    """
    # Get query profile
    query_profile_id = f"ARGO_{wmo_id}_CYC{cycle:03d}"
    query_vec, query_meta = build_profile_vector(query_profile_id, db)
    
    if query_vec is None:
        return []
    
    query_lat = query_meta.get('latitude', 0)
    query_lon = query_meta.get('longitude', 0)
    
    # Get all candidate profiles from database
    candidates_query = db.query(ArgoProfile).filter(
        ArgoProfile.qc_status.in_(['QC_PASS_FLAG_1', 'QC_PASS_FLAG_2'])
    )
    
    if exclude_same_float:
        candidates_query = candidates_query.filter(ArgoProfile.wmo_id != wmo_id)
    
    candidate_profiles = candidates_query.all()
    
    if not candidate_profiles:
        return []
    
    # Score all candidates
    results = []
    for cand in candidate_profiles:
        cand_id = cand.profile_id
        cand_vec, cand_meta = build_profile_vector(cand_id, db)
        
        if cand_vec is None:
            continue
        
        # Cosine similarity check (fast filter)
        cos_sim = cosine_similarity(query_vec, cand_vec)
        if cos_sim < min_cosine:
            continue
        
        # Full composite score
        score = composite_similarity(
            query_vec, query_lat, query_lon,
            cand_vec, cand_meta.get('latitude', 0), cand_meta.get('longitude', 0),
            max_distance_km
        )
        
        if score > 0:
            results.append({
                'profile_id': cand_id,
                'wmo_id': cand_meta.get('wmo_id'),
                'cycle': cand_meta.get('cycle'),
                'date': cand_meta.get('date'),
                'latitude': cand_meta.get('latitude'),
                'longitude': cand_meta.get('longitude'),
                'distance_km': haversine_distance(query_lat, query_lon,
                                                  cand_meta.get('latitude', 0),
                                                  cand_meta.get('longitude', 0)),
                'cosine_similarity': cos_sim,
                'spatial_similarity': spatial_similarity(query_lat, query_lon,
                                                          cand_meta.get('latitude', 0),
                                                          cand_meta.get('longitude', 0),
                                                          max_distance_km),
                'composite_score': score,
                'raw_netcdf_source': cand_meta.get('raw_netcdf_source'),
                'gdac_archive_path': cand_meta.get('gdac_archive_path'),
                'qc_status': cand_meta.get('qc_status')
            })
    
    # Sort by composite score descending
    results.sort(key=lambda x: x['composite_score'], reverse=True)
    
    return results[:n_results]


def format_evidence_citation(match: Dict) -> Dict:
    """
    Format a match into the EvidenceCitation schema for API response.
    """
    return {
        'profile_id': match['profile_id'],
        'wmo_id': match['wmo_id'],
        'cycle': match['cycle'],
        'date': match['date'],
        'latitude': match.get('latitude', 0.0),
        'longitude': match.get('longitude', 0.0),
        'distance_km': round(match['distance_km'], 1),
        'cosine_similarity': round(match['cosine_similarity'], 4),
        'spatial_similarity': round(match['spatial_similarity'], 4),
        'composite_score': round(match['composite_score'], 4),
        'raw_netcdf_source': match['raw_netcdf_source'],
        'gdac_archive_path': match['gdac_archive_path'],
        'qc_status': match['qc_status']
    }


def get_evidence_links(wmo_id: str, cycle: int, db: Session,
                       n_results: int = 3) -> List[Dict]:
    """
    Main entry point: get formatted evidence citations for a forecast.
    """
    matches = find_analogues(wmo_id, cycle, db, n_results=n_results)
    return [format_evidence_citation(m) for m in matches]


if __name__ == "__main__":
    # Quick test with mock data
    print("Testing Evidence-Link matcher...")
    
    # Test cosine similarity
    v1 = np.array([1.0, 2.0, 3.0, 4.0])
    v2 = np.array([1.0, 2.0, 3.0, 4.0])
    v3 = np.array([4.0, 3.0, 2.0, 1.0])
    
    assert abs(cosine_similarity(v1, v2) - 1.0) < 1e-6
    assert cosine_similarity(v1, v3) < 1.0
    
    # Test haversine
    dist = haversine_distance(20.0, 65.0, 20.5, 65.5)
    print(f"Haversine test: {dist:.1f} km")
    
    print("Evidence module basic tests passed")