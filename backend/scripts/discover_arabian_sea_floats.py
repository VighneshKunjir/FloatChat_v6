#!/usr/bin/env python
"""
Discover Arabian Sea floats from the global Argo index.
Finds all floats with profiles in the Arabian Sea bounding box (10-25N, 50-75E)
and ranks them by number of delayed-mode profiles.
"""
import asyncio
import sys
import re
from pathlib import Path
from typing import Dict, List, Tuple, Optional
import httpx
from tqdm import tqdm

# Arabian Sea bounding box
MIN_LAT, MAX_LAT = 10.0, 25.0
MIN_LON, MAX_LON = 50.0, 75.0

GLOBAL_INDEX_URL = "https://data-argo.ifremer.fr/ar_index_global_prof.txt"

INDEX_PATTERN = re.compile(
    r'^([^/]+)/(\d+)/profiles/D(\d+)_(\d{3})D?\.nc,(\d+),([\d.-]+),([\d.-]+),([AIDR]),(\d+),([A-Z]{2}),(\d+)'
)


async def fetch_global_index(client: httpx.AsyncClient) -> str:
    """Fetch the global index file."""
    print("Fetching global index (ar_index_global_prof.txt) - this is ~300MB...")
    resp = await client.get(GLOBAL_INDEX_URL, timeout=300.0)
    resp.raise_for_status()
    print(f"Downloaded {len(resp.text) / 1e6:.1f} MB")
    return resp.text


def parse_years(spec: str) -> set:
    """Parse '2020-2024' or '2022,2023' into a set of years."""
    years: set = set()
    for part in spec.split(","):
        part = part.strip()
        if "-" in part:
            lo, hi = part.split("-", 1)
            years.update(range(int(lo), int(hi) + 1))
        elif part:
            years.add(int(part))
    return years


def parse_index_for_region(content: str, years: set | None = None) -> Dict[str, Dict]:
    """Parse index and extract all floats with profiles in Arabian Sea box."""
    floats = {}
    total_lines = 0
    matched_lines = 0
    
    for line in content.strip().split('\n'):
        total_lines += 1
        if not line or line.startswith('#'):
            continue
        
        match = INDEX_PATTERN.match(line)
        if match:
            dac, wmo, wmo2, cycle_str, date_str, lat_str, lon_str, data_mode, profiler_type, institution, date_update = match.groups()

            if wmo != wmo2:
                continue
            if years is not None:
                try:
                    if int(date_str[:4]) not in years:
                        continue
                except (ValueError, TypeError):
                    continue
            
            lat = float(lat_str)
            lon = float(lon_str)
            
            if MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON:
                matched_lines += 1
                cycle = int(cycle_str)
                
                if wmo not in floats:
                    floats[wmo] = {
                        "dac": dac,
                        "cycles": set(),
                        "positions": [],
                        "data_modes": set(),
                        "institution": institution
                    }
                
                floats[wmo]["cycles"].add(cycle)
                floats[wmo]["positions"].append((lat, lon))
                floats[wmo]["data_modes"].add(data_mode)
    
    print(f"Parsed {total_lines:,} index lines, {matched_lines:,} profiles in Arabian Sea box")
    print(f"Found {len(floats)} unique floats in region")
    
    return floats


def rank_floats(floats: Dict[str, Dict], top_n: Optional[int] = None, min_cycles: int = 0) -> List[Tuple[str, Dict]]:
    """Rank floats by number of delayed-mode cycles, return top N (or all if top_n is None)."""
    ranked = []
    
    for wmo, info in floats.items():
        n_cycles = len(info["cycles"])
        
        if info["positions"]:
            avg_lat = sum(p[0] for p in info["positions"]) / len(info["positions"])
            avg_lon = sum(p[1] for p in info["positions"]) / len(info["positions"])
        else:
            avg_lat = avg_lon = 0
        
        ranked.append((wmo, {
            "dac": info["dac"],
            "n_cycles": n_cycles,
            "cycles": sorted(info["cycles"]),
            "avg_lat": avg_lat,
            "avg_lon": avg_lon,
            "institution": info["institution"],
            "data_modes": info["data_modes"]
        }))
    
    ranked.sort(key=lambda x: x[1]["n_cycles"], reverse=True)
    if min_cycles > 0:
        ranked = [entry for entry in ranked if entry[1]["n_cycles"] >= min_cycles]
    
    return ranked[:top_n] if top_n is not None else ranked


async def main(top_n: Optional[int] = None, output_file: Path = Path("arabian_sea_floats.txt"),
             years: set | None = None, min_cycles: int = 0):
    print("="*70)
    print("ARABIAN SEA FLOAT DISCOVERY FROM GLOBAL INDEX")
    print("="*70)
    print(f"Bounding box: {MIN_LAT}°N-{MAX_LAT}°N, {MIN_LON}°E-{MAX_LON}°E")
    if years:
        print(f"Year filter: {min(years)}-{max(years)}")
    if min_cycles:
        print(f"Minimum cycles: {min_cycles}")
    print()

    timeout = httpx.Timeout(300.0, connect=30.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        content = await fetch_global_index(client)

    print("\nParsing index for Arabian Sea profiles...")
    floats = parse_index_for_region(content, years=years)

    print("\nRanking floats by number of delayed-mode profiles...")
    all_floats = rank_floats(floats, top_n=top_n, min_cycles=min_cycles)
    
    print(f"\n{'='*70}")
    print(f"DISCOVERED {len(all_floats)} ARABIAN SEA FLOATS")
    print(f"{'='*70}")
    print(f"{'#':>3} {'WMO':>10} {'DAC':>10} {'Cycles':>6} {'Avg Lat':>8} {'Avg Lon':>8} {'Inst':>6}")
    print("-"*70)
    
    # Display preview (first 20 entries)
    for i, (wmo, info) in enumerate(all_floats[:20], 1):
        print(f"{i:3d} {wmo:>10} {info['dac']:>10} {info['n_cycles']:6d} {info['avg_lat']:8.3f} {info['avg_lon']:8.3f} {info['institution']:>6}")
    
    if len(all_floats) > 20:
        print(f"... and {len(all_floats) - 20} more floats.")
    
    with open(output_file, "w") as f:
        f.write(f"# Discovered Arabian Sea floats from global index\n")
        f.write(f"# Bounding box: {MIN_LAT}-{MAX_LAT}N, {MIN_LON}-{MAX_LON}E\n")
        if years:
            f.write(f"# Years: {min(years)}-{max(years)}\n")
        if min_cycles:
            f.write(f"# Min cycles: {min_cycles}\n")
        f.write("# Format: WMO,DAC,N_CYCLES,AVG_LAT,AVG_LON,INSTITUTION\n")
        for wmo, info in all_floats:
            f.write(f"{wmo},{info['dac']},{info['n_cycles']},{info['avg_lat']:.4f},{info['avg_lon']:.4f},{info['institution']}\n")
    
    print(f"\nSaved all {len(all_floats)} floats to: {output_file}")
    
    return all_floats


if __name__ == "__main__":
    import argparse as _argparse
    _p = _argparse.ArgumentParser(description="Discover Arabian Sea floats from global Argo index")
    _p.add_argument("--top-n", type=int, default=None, help="Limit number of floats (default: None, returns all)")
    _p.add_argument("--output", type=Path, default=Path("arabian_sea_floats.txt"))
    _p.add_argument("--years", type=str, default=None,
                    help="Profile years, e.g. '2018-2026' or '2022,2023'")
    _p.add_argument("--min-cycles", type=int, default=0,
                    help="Drop floats with fewer delayed-mode cycles")
    _a = _p.parse_args()
    asyncio.run(main(top_n=_a.top_n, output_file=_a.output,
                     years=parse_years(_a.years) if _a.years else None,
                     min_cycles=_a.min_cycles))