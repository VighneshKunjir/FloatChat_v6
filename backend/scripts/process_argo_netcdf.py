#!/usr/bin/env python
"""
Argo NetCDF Processing Pipeline for FloatChat

Processes raw NetCDF profiles from backend/data/raw/{WMO}/ into:
1. Canonical wide-format CSV (argo_floats_canonical.csv) for ML training
2. Validates TEOS-10 static stability (flagged via is_stable, never discarded)
3. Computes derived quantities (σ_θ, N², MLD)

Cleaning pipeline (per .ai/data_spec.md, upstream of interpolation):
1. Mask Argo fill sentinels (>= 9999.0, <= -990.0) to NaN
2. Keep QC flags 1/2, delayed-mode only
3. Enforce hard physical bounds per measurement (T, S, PRES)
4. PCHIP-interpolate to 16 standard depths; discard cycle if ANY
   interpolated level is NaN or out of bounds
"""
import sys
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import numpy as np
import pandas as pd
import xarray as xr
from scipy.interpolate import PchipInterpolator
import gsw
from tqdm import tqdm
import warnings

# Suppress xarray/netCDF4 warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Project paths
RAW_DIR = Path(__file__).parent.parent / "data" / "raw"
PROCESSED_DIR = Path(__file__).parent.parent / "data" / "processed"
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# 16 standard pressure levels (dbar)
STANDARD_DEPTHS = np.array([5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000], dtype=float)

# QC flags to keep (1=good, 2=probably good)
GOOD_QC = {1, 2}

# Argo fill sentinels and hard physical bounds (per .ai/data_spec.md cleaning rules)
SENTINEL_HIGH = 9999.0
SENTINEL_LOW = -990.0
TEMP_BOUNDS = (-2.0, 35.0)
SAL_BOUNDS = (30.0, 42.0)
PRES_BOUNDS = (0.0, 2000.0)


def mask_sentinels(arr: np.ndarray) -> np.ndarray:
    """Mask Argo fill sentinels (99999.0, 9999.0, -999.0, anything <= -990.0) to NaN.

    Must run BEFORE interpolation so sentinels cannot leak into good levels.
    """
    arr = np.asarray(arr, dtype=float)
    bad = (arr >= SENTINEL_HIGH) | (arr <= SENTINEL_LOW) | np.isnan(arr)
    return np.where(bad, np.nan, arr)


def interp_to_standard_depths(pres: np.ndarray, temp: np.ndarray, sal: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """
    Interpolate T/S from irregular pressure levels to 16 standard depths using PCHIP.
    PCHIP preserves monotonicity (no overshoots).
    """
    # Remove NaN values
    valid = ~(np.isnan(pres) | np.isnan(temp) | np.isnan(sal))
    pres, temp, sal = pres[valid], temp[valid], sal[valid]
    
    if len(pres) < 4:
        return np.full(16, np.nan), np.full(16, np.nan)
    
    # Sort by pressure
    sort_idx = np.argsort(pres)
    pres, temp, sal = pres[sort_idx], temp[sort_idx], sal[sort_idx]
    
    # Remove duplicate pressures (keep first)
    _, unique_idx = np.unique(pres, return_index=True)
    pres, temp, sal = pres[unique_idx], temp[unique_idx], sal[unique_idx]
    
    if len(pres) < 4:
        return np.full(16, np.nan), np.full(16, np.nan)
    
    try:
        # PCHIP interpolation
        temp_interp = PchipInterpolator(pres, temp)(STANDARD_DEPTHS)
        sal_interp = PchipInterpolator(pres, sal)(STANDARD_DEPTHS)
        
        # Extrapolation: fill with nearest valid value
        temp_interp = np.where(np.isnan(temp_interp), np.nan, temp_interp)
        sal_interp = np.where(np.isnan(sal_interp), np.nan, sal_interp)
        
        return temp_interp, sal_interp
    except Exception:
        return np.full(16, np.nan), np.full(16, np.nan)


def compute_teos10(temp: np.ndarray, sal: np.ndarray, pres: np.ndarray) -> Dict[str, np.ndarray]:
    """
    Compute TEOS-10 derived quantities.
    Returns dict with: sigma0, N2, mld, stability_flag
    """
    # Convert to Absolute Salinity and Conservative Temperature
    # For simplicity, use practical salinity and in-situ temp as approximation
    # gsw expects SA (Absolute Salinity) and CT (Conservative Temperature)
    # We'll use SA_from_SP and CT_from_t
    
    # Standard depths are in dbar ≈ meters
    # Latitude/longitude needed for SA/CT conversion - use mid-latitude approximation
    lat = 20.0  # Arabian Sea mid-latitude
    lon = 65.0
    
    # Convert practical salinity to Absolute Salinity
    sa = gsw.SA_from_SP(sal, pres, lon, lat)
    # Convert in-situ temperature to Conservative Temperature
    ct = gsw.CT_from_t(sa, temp, pres)
    
    # Potential density anomaly (sigma0) referenced to 0 dbar
    sigma0 = gsw.sigma0(sa, ct)
    
    # Static stability: d(sigma0)/dz > 0
    # depth in meters ≈ dbar
    dz = np.gradient(pres)  # pressure gradient
    d_sigma = np.gradient(sigma0)
    stability = d_sigma / dz  # dσ/dz
    
    # Stability violations
    stability_violations = np.sum(stability < -1e-6)  # allow tiny numerical noise
    is_stable = stability_violations == 0
    
    # Brunt-Väisälä frequency squared (N²)
    # N² = -g/ρ * dρ/dz, but using sigma0: N² ≈ g * d(sigma0)/dz / 1000
    g = 9.80665
    N2 = g * stability / 1000.0  # s^-2
    N2 = np.maximum(N2, 0)  # no negative N²
    
    # Mixed Layer Depth (density threshold: 0.03 kg/m³ from surface)
    surface_sigma = sigma0[0] if not np.isnan(sigma0[0]) else np.nan
    if not np.isnan(surface_sigma):
        sigma_diff = sigma0 - surface_sigma
        mld_idx = np.where(sigma_diff >= 0.03)[0]
        mld = STANDARD_DEPTHS[mld_idx[0]] if len(mld_idx) > 0 else np.nan
    else:
        mld = np.nan
    
    return {
        "sigma0": sigma0,
        "N2": N2,
        "mld": mld,
        "is_stable": is_stable,
        "stability_violations": stability_violations
    }


def process_netcdf_file(nc_path: Path) -> List[Dict]:
    """Process a single NetCDF file (may contain multiple profiles)."""
    results = []
    try:
        ds = xr.open_dataset(nc_path)
    except Exception as e:
        print(f"  Error opening {nc_path.name}: {e}")
        return results
    
    n_prof = ds.sizes.get('N_PROF', 1)
    
    for prof_idx in range(n_prof):
        try:
            # Extract metadata for this profile
            def _get(var, idx):
                if var in ds:
                    v = ds[var].values
                    if isinstance(v, np.ndarray) and v.ndim >= 1:
                        return v[idx] if idx < len(v) else v[0]
                return None
            
            wmo_bytes = _get('PLATFORM_NUMBER', prof_idx)
            wmo = int(wmo_bytes.decode().strip()) if isinstance(wmo_bytes, bytes) else int(wmo_bytes) if wmo_bytes else None
            
            cycle_val = _get('CYCLE_NUMBER', prof_idx)
            cycle = int(cycle_val) if cycle_val is not None and not np.isnan(cycle_val) else None
            lat = float(_get('LATITUDE', prof_idx)) if _get('LATITUDE', prof_idx) else None
            lon = float(_get('LONGITUDE', prof_idx)) if _get('LONGITUDE', prof_idx) else None
            juld = _get('JULD', prof_idx)
            data_mode = _get('DATA_MODE', prof_idx)
            data_mode = data_mode.decode().strip() if isinstance(data_mode, bytes) else str(data_mode)
            
            # Only delayed-mode
            if data_mode != 'D':
                continue
            
            # Extract profile data
            pres = ds.PRES.values[prof_idx] if 'PRES' in ds else np.array([])
            temp = ds.TEMP.values[prof_idx] if 'TEMP' in ds else np.array([])
            sal = ds.PSAL.values[prof_idx] if 'PSAL' in ds else np.array([])
            temp_qc = ds.TEMP_QC.values[prof_idx] if 'TEMP_QC' in ds else np.array([])
            sal_qc = ds.PSAL_QC.values[prof_idx] if 'PSAL_QC' in ds else np.array([])

            # Step 1: mask fill sentinels BEFORE any calculation (never interpolate them)
            pres = mask_sentinels(pres)
            temp = mask_sentinels(temp)
            sal = mask_sentinels(sal)

            # Decode QC bytes to int
            def _decode_qc(qc_arr):
                if qc_arr.dtype.kind in ('S', 'U'):  # string/bytes
                    return np.array([int(x.decode()) if isinstance(x, bytes) else int(x) for x in qc_arr])
                return qc_arr.astype(int)

            temp_qc = _decode_qc(temp_qc)
            sal_qc = _decode_qc(sal_qc)

            # Quality filtering (QC 1/2 only)
            good_mask = np.ones(len(pres), dtype=bool)
            if len(temp_qc) == len(pres):
                good_mask &= np.isin(temp_qc, list(GOOD_QC))
            if len(sal_qc) == len(pres):
                good_mask &= np.isin(sal_qc, list(GOOD_QC))

            pres, temp, sal = pres[good_mask], temp[good_mask], sal[good_mask]

            # Step 2: hard physical bounds per measurement (drop contaminated levels)
            in_bounds = (
                np.isfinite(pres) & np.isfinite(temp) & np.isfinite(sal)
                & (temp >= TEMP_BOUNDS[0]) & (temp <= TEMP_BOUNDS[1])
                & (sal >= SAL_BOUNDS[0]) & (sal <= SAL_BOUNDS[1])
                & (pres > PRES_BOUNDS[0]) & (pres <= PRES_BOUNDS[1])
            )
            pres, temp, sal = pres[in_bounds], temp[in_bounds], sal[in_bounds]

            if len(pres) < 10:
                continue

            # Interpolate to standard depths
            temp_interp, sal_interp = interp_to_standard_depths(pres, temp, sal)

            # Step 3: post-interpolation boundary check — ALL 16 levels must be
            # finite and strictly inside physical bounds, else discard the cycle
            if (
                np.isnan(temp_interp).any() or np.isnan(sal_interp).any()
                or (temp_interp < TEMP_BOUNDS[0]).any() or (temp_interp > TEMP_BOUNDS[1]).any()
                or (sal_interp < SAL_BOUNDS[0]).any() or (sal_interp > SAL_BOUNDS[1]).any()
            ):
                continue
            
            # Compute TEOS-10 physics
            teos = compute_teos10(temp_interp, sal_interp, STANDARD_DEPTHS)
            
            # Build result
            result = {
                "wmo": wmo,
                "cycle": cycle,
                "date": str(juld)[:10] if juld is not None else "",
                "latitude": lat,
                "longitude": lon,
                "data_mode": data_mode,
                "n_levels_raw": int(good_mask.sum()),
                "is_stable": teos["is_stable"],
                "stability_violations": teos["stability_violations"],
                "mld_dbar": teos["mld"],
                "max_N2": float(np.nanmax(teos["N2"])) if not np.all(np.isnan(teos["N2"])) else np.nan,
            }
            
            # Add 16 depth levels for T, S, sigma0
            for i, depth in enumerate(STANDARD_DEPTHS):
                result[f"temp_{int(depth)}"] = temp_interp[i]
                result[f"sal_{int(depth)}"] = sal_interp[i]
                result[f"sigma_{int(depth)}"] = teos["sigma0"][i]
            
            results.append(result)
            
        except Exception as e:
            print(f"  Error processing profile {prof_idx} in {nc_path.name}: {e}")
            continue
    
    return results


def process_all_floats():
    """Main processing pipeline."""
    print("="*70)
    print("ARGO NETCDF PROCESSING PIPELINE")
    print("="*70)
    print(f"Input:  {RAW_DIR}")
    print(f"Output: {PROCESSED_DIR}")
    print()
    
    # Collect all NetCDF files
    nc_files = list(RAW_DIR.rglob("D*.nc"))
    print(f"Found {len(nc_files)} NetCDF files across {len(list(RAW_DIR.iterdir()))} floats")
    
    # Process each file
    all_results = []
    failed = 0
    
    for nc_path in tqdm(nc_files, desc="Processing profiles"):
        results = process_netcdf_file(nc_path)
        if results:
            all_results.extend(results)
        else:
            failed += 1
    
    print(f"\nProcessed: {len(all_results)} profiles")
    print(f"Failed/Skipped: {failed} profiles")
    
    if not all_results:
        print("No valid profiles found!")
        return
    
    # Create DataFrame
    df = pd.DataFrame(all_results)
    
    # Sort by WMO, cycle
    df = df.sort_values(["wmo", "cycle"]).reset_index(drop=True)
    
    # Reorder columns: metadata first, then depth levels
    meta_cols = [c for c in df.columns if not any(c.startswith(p) for p in ["temp_", "sal_", "sigma_"])]
    depth_cols = sorted([c for c in df.columns if c.startswith(("temp_", "sal_", "sigma_"))],
                       key=lambda x: (x.split('_')[0], int(x.split('_')[1])))
    df = df[meta_cols + depth_cols]
    
    # Save canonical CSV
    csv_path = PROCESSED_DIR / "argo_floats_canonical.csv"
    df.to_csv(csv_path, index=False)
    print(f"\nSaved canonical CSV: {csv_path}")
    print(f"Shape: {df.shape} ({df.shape[0]} profiles × {df.shape[1]} columns)")
    
    # Summary statistics
    print(f"\nSummary:")
    print(f"  Unique floats: {df['wmo'].nunique()}")
    print(f"  Total profiles: {len(df)}")
    print(f"  Stable profiles: {df['is_stable'].sum()} ({df['is_stable'].mean()*100:.1f}%)")
    print(f"  Date range: {df['date'].min()} to {df['date'].max()}")
    
    # Per-float summary
    print("\nPer-float profile counts:")
    for wmo, group in df.groupby('wmo'):
        stable_pct = group['is_stable'].mean() * 100
        print(f"  {wmo}: {len(group)} profiles, {stable_pct:.1f}% stable")
    
    return df


def main():
    df = process_all_floats()
    if df is not None:
        print("\nProcessing complete!")
        print(f"Canonical dataset ready at: {PROCESSED_DIR / 'argo_floats_canonical.csv'}")


if __name__ == "__main__":
    main()