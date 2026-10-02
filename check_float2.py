import sys
sys.path.insert(0, 'backend/scripts')
from process_argo_netcdf import process_netcdf_file, STANDARD_DEPTHS
from pathlib import Path

# Test processing a 5905082 file
nc_path = Path('backend/data/raw/5905082/D5905082_032.nc')
results = process_netcdf_file(nc_path)
print(f'Results for {nc_path.name}: {len(results)} profiles returned')
if results:
    for r in results:
        print(f'  WMO: {r["wmo"]}, Cycle: {r["cycle"]}, Date: {r["date"]}, Lat: {r["latitude"]}, Lon: {r["longitude"]}')
        print(f'  Raw levels: {r["n_levels_raw"]}, Stable: {r["is_stable"]}')
        # Check temp values
        temps = [r[f"temp_{int(d)}"] for d in STANDARD_DEPTHS]
        sals = [r[f"sal_{int(d)}"] for d in STANDARD_DEPTHS]
        print(f'  Temp range: {min(temps):.2f} - {max(temps):.2f}')
        print(f'  Sal range: {min(sals):.2f} - {max(sals):.2f}')
else:
    print('  NO RESULTS - filtered out!')

# Check all files for this float
float_dir = Path('backend/data/raw/5905082')
nc_files = list(float_dir.glob('D*.nc'))
total_results = 0
for nc in nc_files[:10]:  # Check first 10
    results = process_netcdf_file(nc)
    if results:
        total_results += len(results)
        print(f'{nc.name}: {len(results)} profiles')
    else:
        print(f'{nc.name}: 0 profiles (filtered out)')
print(f'\nTotal from first 10 files: {total_results} profiles')