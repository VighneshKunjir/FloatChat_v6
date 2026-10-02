#!/usr/bin/env python
"""
Argo GDAC NetCDF Downloader for Arabian Sea Floats
Prompts user for count and date range dynamically.
"""
import argparse
import asyncio
import sys
import re
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import httpx
from tqdm import tqdm

GLOBAL_INDEX_URL = "https://data-argo.ifremer.fr/ar_index_global_prof.txt"
BASE_URL = "https://data-argo.ifremer.fr/dac"

# Arabian Sea Bounding Box
MIN_LAT, MAX_LAT = 10.0, 25.0
MIN_LON, MAX_LON = 50.0, 75.0


def parse_global_index_dynamic(content: str, start_year: Optional[int] = None, end_year: Optional[int] = None) -> Dict[str, Dict]:
    """Parse index dynamically for Arabian Sea region without hardcoded WMOs."""
    floats = {}
    pattern = r'^([^/]+)/(\d+)/profiles/D(\d+)_(\d{3})D?\.nc,(\d+),([\d.-]+),([\d.-]+)'
    
    for line in content.strip().split('\n'):
        if not line or line.startswith('#'):
            continue
        
        match = re.match(pattern, line)
        if match:
            dac, wmo, wmo2, cycle, date_str, lat_str, lon_str = match.groups()
            if wmo != wmo2:
                continue
            
            lat = float(lat_str)
            lon = float(lon_str)
            
            # Check bounding box
            if MIN_LAT <= lat <= MAX_LAT and MIN_LON <= lon <= MAX_LON:
                # Filter by year
                if date_str and len(date_str) >= 4:
                    year = int(date_str[:4])
                    if start_year and year < start_year:
                        continue
                    if end_year and year > end_year:
                        continue
                
                if wmo not in floats:
                    floats[wmo] = {"dac": dac, "cycles": []}
                
                floats[wmo]["cycles"].append(int(cycle))
                
    # Sort cycles for each float
    for wmo in floats:
        floats[wmo]["cycles"] = sorted(list(set(floats[wmo]["cycles"])))
        
    return floats


class ArgoDownloader:
    def __init__(self, output_dir: Path, max_concurrent: int = 3):
        self.output_dir = output_dir
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
        
    def get_profile_url(self, dac: str, wmo: str, cycle: int) -> str:
        cycle_str = f"{cycle:03d}"
        return f"{BASE_URL}/{dac}/{wmo}/profiles/D{wmo}_{cycle_str}.nc"
    
    async def download_profile(self, client: httpx.AsyncClient, dac: str, wmo: str, cycle: int, 
                               progress_bar: Optional[tqdm] = None) -> bool:
        url = self.get_profile_url(dac, wmo, cycle)
        output_path = self.output_dir / wmo / f"D{wmo}_{cycle:03d}.nc"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Skip if file already exists
        if output_path.exists():
            if progress_bar:
                progress_bar.update(1)
            return True
        
        async with self.semaphore:
            try:
                async with client.stream("GET", url, timeout=60.0, follow_redirects=True) as resp:
                    if resp.status_code == 404:
                        return False
                    resp.raise_for_status()
                    
                    with open(output_path, "wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=8192):
                            f.write(chunk)
                
                if progress_bar:
                    progress_bar.update(1)
                return True
                
            except Exception as e:
                if output_path.exists():
                    output_path.unlink()
                if progress_bar:
                    progress_bar.update(1)
                return False
    
    async def download_float(self, client: httpx.AsyncClient, wmo: str, dac: str, cycles: List[int]) -> Dict:
        if not cycles:
            return {"wmo": wmo, "downloaded": 0, "total": 0}
        
        with tqdm(total=len(cycles), desc=f"  Float {wmo}", unit="file") as pbar:
            tasks = [
                self.download_profile(client, dac, wmo, cycle, pbar)
                for cycle in cycles
            ]
            results = await asyncio.gather(*tasks)
            downloaded = sum(results)
        
        return {"wmo": wmo, "downloaded": downloaded, "total": len(cycles)}


def prompt_user_parameters(total_found: int) -> Tuple[Optional[int], Optional[int], Optional[int]]:
    """Interactively ask the user for float limit and date ranges."""
    print("\n" + "="*70)
    print("DOWNLOAD CONFIGURATION PROMPT")
    print("="*70)
    
    # 1. Ask for Float Count
    count_input = input(f"How many floats to download? (Found {total_found} total, press Enter or type 'all' for ALL): ").strip().lower()
    if not count_input or count_input == 'all':
        float_limit = None
    else:
        try:
            float_limit = int(count_input)
        except ValueError:
            print("Invalid input, defaulting to ALL floats.")
            float_limit = None

    # 2. Ask for Time Period
    years_input = input("Enter time period (e.g. '2018-2026', '2023', or press Enter for NO FILTER): ").strip()
    start_year, end_year = None, None
    if years_input:
        if "-" in years_input:
            parts = years_input.split("-")
            start_year, end_year = int(parts[0]), int(parts[1])
        else:
            start_year = end_year = int(years_input)

    return float_limit, start_year, end_year


async def main():
    parser = argparse.ArgumentParser(description="Download Argo profiles interactively")
    parser.add_argument("--output", "-o", type=Path, default=Path("../data/raw"), help="Output directory")
    args = parser.parse_args()

    async with httpx.AsyncClient(timeout=300.0) as client:
        print("Fetching global index (ar_index_global_prof.txt)...")
        resp = await client.get(GLOBAL_INDEX_URL)
        resp.raise_for_status()

        # Prompt user
        print("\nDiscovering Arabian Sea floats...")
        all_floats = parse_global_index_dynamic(resp.text)
        
        float_limit, start_year, end_year = prompt_user_parameters(len(all_floats))

        # Re-parse with year filter if specified
        if start_year or end_year:
            print("\nApplying year filter...")
            floats = parse_global_index_dynamic(resp.text, start_year=start_year, end_year=end_year)
        else:
            floats = all_floats

        # Sort floats by number of available cycles
        sorted_floats = sorted(floats.items(), key=lambda x: len(x[1]["cycles"]), reverse=True)

        # Apply float limit
        if float_limit:
            selected_floats = sorted_floats[:float_limit]
        else:
            selected_floats = sorted_floats

        print(f"\nReady to download {len(selected_floats)} float(s).")
        confirm = input("Proceed with download? [y/N]: ").strip().lower()
        if confirm != 'y':
            print("Download cancelled.")
            return

        downloader = ArgoDownloader(args.output)
        for wmo, info in selected_floats:
            print(f"\nProcessing WMO: {wmo} ({len(info['cycles'])} cycles, DAC: {info['dac']})")
            await downloader.download_float(client, wmo, info['dac'], info['cycles'])

        print(f"\n{'='*60}\nDOWNLOAD COMPLETE\nSaved files to: {args.output}\n{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())