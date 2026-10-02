import xarray as xr
import pandas as pd
from pathlib import Path

# Check 5905082 in detail
raw_dir = Path('backend/data/raw')
wmo = '5905082'
float_dir = raw_dir / wmo
nc_files = list(float_dir.glob('D*.nc'))
print(f'{wmo}: {len(nc_files)} files')

# Check first file in detail
nc = nc_files[0]
ds = xr.open_dataset(nc)
print(f'  {nc.name}: N_PROF={ds.sizes.get("N_PROF", 1)}')
print(f'  DATA_MODE: {ds.DATA_MODE.values}')

prof_idx = 0
pres = ds.PRES.values[prof_idx] if 'PRES' in ds else None
temp = ds.TEMP.values[prof_idx] if 'TEMP' in ds else None
sal = ds.PSAL.values[prof_idx] if 'PSAL' in ds else None

print(f'  PRES shape: {pres.shape if pres is not None else None}')
print(f'  TEMP shape: {temp.shape if temp is not None else None}')
print(f'  PSAL shape: {sal.shape if sal is not None else None}')

if pres is not None:
    print(f'  PRES range: {pres.min():.1f} - {pres.max():.1f}')
    print(f'  PRES valid: {sum(~pd.isna(pres))}/{len(pres)}')
if temp is not None:
    print(f'  TEMP range: {temp.min():.2f} - {temp.max():.2f}')
    print(f'  TEMP valid: {sum(~pd.isna(temp))}/{len(temp)}')
if sal is not None:
    print(f'  PSAL range: {sal.min():.2f} - {sal.max():.2f}')
    print(f'  PSAL valid: {sum(~pd.isna(sal))}/{len(sal)}')