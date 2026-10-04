# Argo NetCDF Discovery & Downloader - User Guide

Complete reference guide for `discover_arabian_sea_floats.py` and `download_argo_netcdf.py`.

---

## Overview of Key Features

1. **Discovery Script (`discover_arabian_sea_floats.py`)**:
   * Scans the global Argo index (`ar_index_global_prof.txt`) for all profiles located within the Arabian Sea bounding box ($10^\circ\text{N}–25^\circ\text{N}, 50^\circ\text{E}–75^\circ\text{E}$).
   * Discovers **ALL** floats in the region by default (or restricts output to the top $N$ floats if specified).

2. **Downloader Script (`download_argo_netcdf.py`)**:
   * Interactively prompts for the **number of floats** to download and the **target date range** at runtime.
   * Dynamically ranks floats by profile count within the specified geographic and temporal constraints.
   * Automatically skips profile files that already exist in the target directory to allow for seamless download resuming.

---

## 1. Discovering Floats (`discover_arabian_sea_floats.py`)

Scans the global Argo index to locate all floats operating within the Arabian Sea bounding box.

### Usage Commands

```bash
# Discover ALL floats in the Arabian Sea (Default)
python discover_arabian_sea_floats.py

# Save discovered float list to a specific file
python discover_arabian_sea_floats.py --output arabian_sea_floats.txt

# Filter discovery by a specific year range (e.g., past 8 years: 2018-2026)
python discover_arabian_sea_floats.py --years 2018-2026

# Limit discovery to the top N floats ranked by profile count
python discover_arabian_sea_floats.py --top-n 100
```

### Discovery Command Options

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| `--output` | | Destination text file for discovered floats (default: `arabian_sea_floats.txt`) | `--output my_floats.txt` |
| `--top-n` | | Limit results to top $N$ floats by profile count (default: `None` / returns all) | `--top-n 50` |
| `--years` | | Filter index by year or year range | `--years 2018-2026` or `--years 2022,2023` |
| `--min-cycles` | | Drop floats with fewer than $N$ delayed-mode profiles | `--min-cycles 10` |

---

## 2. Downloading Profiles (`download_argo_netcdf.py`)

Fetches NetCDF profile files directly from IFREMER GDAC servers using interactive user prompts.

### Usage Commands

```bash
# Launch downloader with default output directory (../data/raw)
python download_argo_netcdf.py

# Specify a custom download folder (use double quotes if path contains spaces)
python download_argo_netcdf.py --output "E:\Projects\ArgoData Raw\floats"
```

### Interactive Prompt Example

Upon launch, the script prompts for setup parameters:

```text
======================================================================
DOWNLOAD CONFIGURATION PROMPT
======================================================================
How many floats to download? (Found 342 total, press Enter or type 'all' for ALL): 100
Enter time period (e.g. '2018-2026', '2023', or press Enter for NO FILTER): 2018-2026

Ready to download 100 float(s).
Proceed with download? [y/N]: y
```

---

## File Organization & Output Structure

Downloaded files are stored in individual subdirectories named after each float's WMO ID inside the specified output directory:

```text
"E:\Projects\ArgoData Raw\floats"\
├── 6903059\
│   ├── D6903059_001.nc
│   ├── D6903059_002.nc
│   └── ...
├── 2900090\
│   ├── D2900090_001.nc
│   └── ...
└── ...
```

---

## Key Operational Behaviors

| Feature | Behavior |
|---------|----------|
| **Resume & Skip Existing** | Files already saved on disk (`D<WMO>_<CYCLE>.nc`) are recognized and skipped instantly without repeating HTTP requests. |
| **Path Spaces** | Always wrap destination file paths containing spaces inside double quotes (`"..."`) when passing the `--output` parameter. |
| **Interruption Handling** | Interrupted downloads (e.g., `Ctrl+C`) can be resumed by re-running the command; existing files will be preserved. |
| **Corrupt File Cleanup** | If a file transfer breaks mid-stream, incomplete files are cleaned up to prevent corrupted data storage. |

---

## Example Workflows

### Workflow 1: Interactive Download (Top 100 Floats over 8 Years)
1. Run `python download_argo_netcdf.py -o "E:\Projects\ArgoData Raw\floats"`.
2. When prompted for float count, type `100`.
3. When prompted for time period, type `2018-2026`.
4. Confirm with `y`.

### Workflow 2: Export Float Manifest First
1. Export a manifest of all active Arabian Sea floats:
   ```bash
   python discover_arabian_sea_floats.py --years 2018-2026 --output arabian_sea_all_8yrs.txt
   ```
2. Download data using interactive selection:
   ```bash
   python download_argo_netcdf.py --output "./raw_netcdf"
   ```