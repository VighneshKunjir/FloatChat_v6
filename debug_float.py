import sys
sys.path.insert(0, 'backend/scripts')
from process_argo_netcdf import process_netcdf_file, interp_to_standard_depths, mask_sentinels, compute_teos10, STANDARD_DEPTHS
from pathlib import Path
import xarray as xr
import numpy as np
import pandas as pd

# Debug D5905082_032.nc in detail
nc_path = Path('backend/data/raw/5905082/D5905082_032.nc')
ds = xr.open_dataset(nc_path)

n_prof = ds.sizes.get('N_PROF', 1)
print(f'N_PROF: {n_prof}')

prof_idx = 0
wmo_bytes = ds.PLATFORM_NUMBER.values
wmo = int(wmo_bytes.decode().strip()) if isinstance(wmo_bytes, bytes) else int(wmo_bytes)
cycle_val = ds.CYCLE_NUMBER.values
cycle = int(cycle_val[0]) if hasattr(cycle_val, '__len__') else int(cycle_val)
lat = float(ds.LATITUDE.values[0]) if 'LATITUDE' in ds else None
lon = float(ds.LONGITUDE.values[0]) if 'LONGITUDE' in ds else None
juld = ds.JULD.values[0] if 'JULD' in ds else None
data_mode = ds.DATA_MODE.values[0]
data_mode = data_mode.decode().strip() if isinstance(data_mode, bytes) else str(data_mode)

print(f'WMO: {wmo}, Cycle: {cycle}, Lat: {lat}, Lon: {lon}, Date: {juld}, DataMode: {data_mode}')

pres = ds.PRES.values[prof_idx]
temp = ds.TEMP.values[prof_idx]
sal = ds.PSAL.values[prof_idx]
temp_qc = ds.TEMP_QC.values[prof_idx]
sal_qc = ds.PSAL_QC.values[prof_idx]

print(f'\nRaw data:')
print(f'  PRES: {len(pres)} levels, range {pres.min():.1f}-{pres.max():.1f}')
print(f'  TEMP: {len(temp)} levels, range {temp.min():.2f}-{temp.max():.2f}')
print(f'  PSAL: {len(sal)} levels, range {sal.min():.2f}-{sal.max():.2f}')

# Decode QC
def _decode_qc(qc_arr):
    if qc_arr.dtype.kind in ('S', 'U'):
        return np.array([int(x.decode()) if isinstance(x, bytes) else int(x) for x in qc_arr])
    return qc_arr.astype(int)

temp_qc = _decode_qc(temp_qc)
sal_qc = _decode_qc(sal_qc)

print(f'  TEMP_QC: unique={np.unique(temp_qc)}')
print(f'  PSAL_QC: unique={np.unique(sal_qc)}')

# Step 1: mask sentinels
pres = mask_sentinels(pres)
temp = mask_sentinels(temp)
sal = mask_sentinels(sal)
print(f'\nAfter sentinel masking:')
print(f'  PRES valid: {np.isfinite(pres).sum()}/{len(pres)}')
print(f'  TEMP valid: {np.isfinite(temp).sum()}/{len(temp)}')
print(f'  PSAL valid: {np.isfinite(sal).sum()}/{len(sal)}')

# QC filtering
good_mask = np.ones(len(pres), dtype=bool)
good_mask &= np.isin(temp_qc, [1, 2])
good_mask &= np.isin(sal_qc, [1, 2])
print(f'After QC filtering: {good_mask.sum()}/{len(pres)} levels')
pres, temp, sal = pres[good_mask], temp[good_mask], sal[good_mask]

# Step 2: physical bounds
TEMP_BOUNDS = (-2.0, 35.0)
SAL_BOUNDS = (30.0, 42.0)
PRES_BOUNDS = (0.0, 2000.0)

in_bounds = (
    np.isfinite(pres) & np.isfinite(temp) & np.isfinite(sal)
    & (temp >= TEMP_BOUNDS[0]) & (temp <= TEMP_BOUNDS[1])
    & (sal >= SAL_BOUNDS[0]) & (sal <= SAL_BOUNDS[1])
    & (pres > PRES_BOUNDS[0]) & (pres <= PRES_BOUNDS[1])
)
print(f'After physical bounds: {in_bounds.sum()}/{len(pres)} levels')
pres, temp, sal = pres[in_bounds], temp[in_bounds], sal[in_bounds]

print(f'\nFinal levels for interpolation: {len(pres)}')
print(f'  PRES range: {pres.min():.1f}-{pres.max():.1f}')
print(f'  TEMP range: {temp.min():.2f}-{temp.max():.2f}')
print(f'  PSAL range: {sal.min():.2f}-{sal.max():.2f}')

# Interpolation
temp_interp, sal_interp = interp_to_standard_depths(pres, temp, sal)
print(f'\nInterpolation results:')
print(f'  Temp interp: {np.isnan(temp_interp).sum()} NaN out of 16')
print(f'  Sal interp: {np.isnan(sal_interp).sum()} NaN out of 16')
print(f'  Temp interp range: {np.nanmin(temp_interp):.2f}-{np.nanmax(temp_interp):.2f}')
print(f'  Sal interp range: {np.nanmin(sal_interp):.2f}-{np.nanmax(sal_interp):.2f}')

# Check bounds
print(f'\nPost-interpolation bounds check:')
print(f'  Temp in bounds: {np.all((temp_interp >= TEMP_BOUNDS[0]) & (temp_interp <= TEMP_BOUNDS[1]))}')
print(f'  Sal in bounds: {np.all((sal_interp >= SAL_BOUNDS[0]) & (sal_interp <= SAL_BOUNDS[1]))}')
print(f'  All finite: {np.all(np.isfinite(temp_interp)) and np.all(np.isfinite(sal_interp))}')