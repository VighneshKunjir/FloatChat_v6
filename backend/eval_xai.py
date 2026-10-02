"""Comprehensive XAI evaluation script."""
import sys
sys.path.insert(0, '.')

import torch
import numpy as np
from app.ml.model import PhysicsInformedBiLSTM, get_device
from app.ml.xai import compute_xai_attribution, compute_integrated_gradients
from sklearn.preprocessing import StandardScaler
import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

# Load data
csv_path = Path(__file__).parent / 'data' / 'processed' / 'argo_30floats_canonical.csv'
df = pd.read_csv(csv_path)

STANDARD_DEPTHS = [5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]
TEMP_COLS = [f'temp_{d}' for d in STANDARD_DEPTHS]
SAL_COLS = [f'sal_{d}' for d in STANDARD_DEPTHS]

df = df.dropna(subset=TEMP_COLS + SAL_COLS).reset_index(drop=True)

# Float-level spatial split
ARCTIC_WMOS = {6903058, 6903059, 6903060, 6903062, 6903063}
wmos = sorted(df['wmo'].unique().tolist())
arabian = sorted(set(wmos) - ARCTIC_WMOS)
_, test_ar = train_test_split(arabian, test_size=5, random_state=42)
test_df = df[df['wmo'].isin(test_ar)].reset_index(drop=True)
train_df = df[~df['wmo'].isin(test_ar)].reset_index(drop=True)

# Fit scalers
temp_scaler = StandardScaler().fit(train_df[TEMP_COLS].to_numpy(dtype=np.float64))
sal_scaler = StandardScaler().fit(train_df[SAL_COLS].to_numpy(dtype=np.float64))

# Build one test window
def build_windows(df):
    Xs, yTs, ySs, metas = [], [], [], []
    for wmo, g in df.sort_values(['wmo', 'cycle']).groupby('wmo'):
        g = g.dropna(subset=TEMP_COLS + SAL_COLS + ['cycle']).reset_index(drop=True)
        if len(g) < 4:
            continue
        t = g[TEMP_COLS].to_numpy(dtype=np.float32)
        s = g[SAL_COLS].to_numpy(dtype=np.float32)
        cyc = g['cycle'].to_numpy()
        for i in range(len(g) - 3):
            seq_t = t[i:i+3]
            seq_s = s[i:i+3]
            x = np.concatenate([seq_t, seq_s], axis=1)
            Xs.append(x)
            yTs.append(t[i+3])
            ySs.append(s[i+3])
            metas.append((int(wmo), int(cyc[i+3])))
    return np.stack(Xs), np.stack(yTs), np.stack(ySs), metas

def scale_frame(frame):
    t = temp_scaler.transform(frame[TEMP_COLS].to_numpy(dtype=np.float64)).astype(np.float32)
    s = sal_scaler.transform(frame[SAL_COLS].to_numpy(dtype=np.float64)).astype(np.float32)
    out = frame.copy()
    out[TEMP_COLS] = t
    out[SAL_COLS] = s
    return out

Xte, yTte, ySte, test_metas = build_windows(scale_frame(test_df))

# Load model
device = get_device()
model = PhysicsInformedBiLSTM().to(device)
artifacts_dir = Path(__file__).parent / 'app' / 'ml' / 'artifacts'
model.load_state_dict(torch.load(artifacts_dir / 'model_weights.pt', map_location=device))
model.eval()

# Test XAI for temperature at different depths
print('=== XAI ATTRIBUTION AT DIFFERENT DEPTHS ===')
for depth_idx in [0, 4, 8, 15]:  # Surface, 100dbar, 300dbar, 1000dbar
    input_tensor = torch.from_numpy(Xte[:1].astype(np.float32)).to(device)
    xai_result = compute_xai_attribution(model, input_tensor, target_variable='temp', target_depth_idx=depth_idx)
    print('Depth idx:', depth_idx, 'Depth:', STANDARD_DEPTHS[depth_idx], 'dbar')
    print('  Convergence delta:', xai_result['convergence_delta'])
    temp_attr = xai_result['temporal_attribution']
    total = sum(a['importance_score'] for a in temp_attr)
    print('  Temporal sum:', total)
    for a in temp_attr:
        print('   ', a['cycle_label'], ':', a['importance_score'])
    print()

# Test for salinity too
print('=== XAI FOR SALINITY (100 dbar) ===')
input_tensor = torch.from_numpy(Xte[:1].astype(np.float32)).to(device)
xai_result = compute_xai_attribution(model, input_tensor, target_variable='sal', target_depth_idx=4)
print('Convergence delta:', xai_result['convergence_delta'])
temp_attr = xai_result['temporal_attribution']
total = sum(a['importance_score'] for a in temp_attr)
print('  Temporal sum:', total)
for a in temp_attr:
    print('   ', a['cycle_label'], ':', a['importance_score'])

# Verify the baseline tensor behavior
print()
print('=== BASELINE VERIFICATION ===')
input_tensor = torch.from_numpy(Xte[:1].astype(np.float32)).to(device)
baseline = torch.zeros_like(input_tensor)
attributions, delta = compute_integrated_gradients(model, input_tensor, baseline, 'temp', 4)
print('Attributions shape:', attributions.shape)
print('Delta:', delta)

# Check if baseline produces zero output
model.eval()
with torch.no_grad():
    temp_base, sal_base = model(baseline)
    temp_in, sal_in = model(input_tensor)
    print('Baseline temp output:', temp_base[0, 4].item())
    print('Input temp output:', temp_in[0, 4].item())
    print('Difference:', (temp_in[0, 4] - temp_base[0, 4]).item())
    print('Attribution sum:', attributions.sum())