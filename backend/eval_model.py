"""Comprehensive model evaluation script."""
import sys
sys.path.insert(0, '.')

import torch
import numpy as np
import pandas as pd
import joblib
from pathlib import Path

from app.ml.model import PhysicsInformedBiLSTM, get_device
from app.ml.loss import PhysicsConstrainedLoss
from app.ml.baselines import persistence_predict, train_gradient_boosting, predict_gradient_boosting, profile_metrics, violation_rate_percent
from app.ml.xai import compute_xai_attribution
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import r2_score
from torch.utils.data import DataLoader, TensorDataset

# Load data
csv_path = Path(__file__).parent / 'data' / 'processed' / 'argo_floats_canonical.csv'
df = pd.read_csv(csv_path)

STANDARD_DEPTHS = [5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]
TEMP_COLS = [f'temp_{d}' for d in STANDARD_DEPTHS]
SAL_COLS = [f'sal_{d}' for d in STANDARD_DEPTHS]

df = df.dropna(subset=TEMP_COLS + SAL_COLS).reset_index(drop=True)

# Filter physical ranges
phys_mask = (
    (df[TEMP_COLS].ge(-2.0) & df[TEMP_COLS].le(35.0)).all(axis=1)
    & (df[SAL_COLS].ge(30.0) & df[SAL_COLS].le(42.0)).all(axis=1)
)
df = df[phys_mask].reset_index(drop=True)

# Float-level spatial split (same as training)
ARCTIC_WMOS = {6903058, 6903059, 6903060, 6903062, 6903063}
wmos = sorted(df['wmo'].unique().tolist())
arctic = sorted(set(wmos) & ARCTIC_WMOS)
arabian = sorted(set(wmos) - ARCTIC_WMOS)
train_ar, rest_ar = train_test_split(arabian, test_size=10, random_state=42)
val_ar, test_ar = train_test_split(rest_ar, test_size=5, random_state=42)
train_ac = arctic[:-1] if len(arctic) > 1 else arctic
val_ac = arctic[-1:] if len(arctic) > 1 else []
train_wmos = sorted(train_ar + train_ac)
val_wmos = sorted(val_ar + val_ac)
test_wmos = sorted(test_ar)

print('Test floats:', test_wmos)

train_df = df[df['wmo'].isin(train_wmos)].reset_index(drop=True)
test_df = df[df['wmo'].isin(test_wmos)].reset_index(drop=True)

# Fit scalers on training
temp_scaler = StandardScaler().fit(train_df[TEMP_COLS].to_numpy(dtype=np.float64))
sal_scaler = StandardScaler().fit(train_df[SAL_COLS].to_numpy(dtype=np.float64))

def scale_frame(frame):
    t = temp_scaler.transform(frame[TEMP_COLS].to_numpy(dtype=np.float64)).astype(np.float32)
    s = sal_scaler.transform(frame[SAL_COLS].to_numpy(dtype=np.float64)).astype(np.float32)
    out = frame.copy()
    out[TEMP_COLS] = t
    out[SAL_COLS] = s
    return out

# Build windows
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

Xte, yTte, ySte, test_metas = build_windows(scale_frame(test_df))
print('Test windows:', len(Xte))

# Load model
device = get_device()
model = PhysicsInformedBiLSTM().to(device)
artifacts_dir = Path(__file__).parent / 'app' / 'ml' / 'artifacts'
model.load_state_dict(torch.load(artifacts_dir / 'model_weights.pt', map_location=device))
model.eval()

# Evaluate
test_loader = DataLoader(TensorDataset(torch.from_numpy(Xte), torch.from_numpy(yTte), torch.from_numpy(ySte)), batch_size=32)

t_preds, s_preds = [], []
with torch.no_grad():
    for X, yT, yS in test_loader:
        X = X.to(device)
        pt, ps = model(X)
        t_preds.append(temp_scaler.inverse_transform(pt.cpu().numpy()))
        s_preds.append(sal_scaler.inverse_transform(ps.cpu().numpy()))

t_pred = np.concatenate(t_preds)
s_pred = np.concatenate(s_preds)
t_true = temp_scaler.inverse_transform(yTte)
s_true = sal_scaler.inverse_transform(ySte)

# Metrics
from app.ml.baselines import profile_metrics, violation_rate_percent

print()
print('=== MODEL METRICS ===')
m = profile_metrics(t_true, s_true, t_pred, s_pred, 'FloatChat LSTM')
print('Temp RMSE:', m['profile_rmse'], '°C')
print('Temp MAE:', m['profile_mae'], '°C')
print('Thermocline RMSE:', m['thermocline_rmse'], '°C')
print('Deep RMSE:', m['deep_rmse'], '°C')
print('Physical Violation Rate:', m['physical_violation_rate'], '%')
print('Temp R2:', r2_score(t_true.flatten(), t_pred.flatten()))
print('Sal R2:', r2_score(s_true.flatten(), s_pred.flatten()))

# Salinity metrics
sal_rmse = np.sqrt(np.mean((s_pred - s_true) ** 2))
sal_mae = np.mean(np.abs(s_pred - s_true))
print('Sal RMSE:', sal_rmse, 'PSU')
print('Sal MAE:', sal_mae, 'PSU')

# Persistence baseline
p_t, p_s = persistence_predict(Xte)
p_t_phys = temp_scaler.inverse_transform(p_t)
p_s_phys = sal_scaler.inverse_transform(p_s)
pm = profile_metrics(t_true, s_true, p_t_phys, p_s_phys, 'Persistence')
print()
print('=== PERSISTENCE BASELINE ===')
print('Temp RMSE:', pm['profile_rmse'], '°C')
print('Temp MAE:', pm['profile_mae'], '°C')
print('Physical Violation Rate:', pm['physical_violation_rate'], '%')

# Gradient Boosting
Xtr, yTtr, yStr, _ = build_windows(scale_frame(train_df))
gb_models = train_gradient_boosting(Xtr, yTtr, yStr)
gb_t, gb_s = predict_gradient_boosting(gb_models, Xte)
gb_t_phys = temp_scaler.inverse_transform(gb_t)
gb_s_phys = sal_scaler.inverse_transform(gb_s)
gbm = profile_metrics(t_true, s_true, gb_t_phys, gb_s_phys, 'Gradient Boosting')
print()
print('=== GRADIENT BOOSTING ===')
print('Temp RMSE:', gbm['profile_rmse'], '°C')
print('Temp MAE:', gbm['profile_mae'], '°C')
print('Physical Violation Rate:', gbm['physical_violation_rate'], '%')

# XAI test
print()
print('=== XAI VERIFICATION ===')
input_tensor = torch.from_numpy(Xte[:1].astype(np.float32)).to(device)
xai_result = compute_xai_attribution(model, input_tensor, target_variable='temp', target_depth_idx=4)
print('Convergence delta:', xai_result['convergence_delta'])
temp_attr = xai_result['temporal_attribution']
print('Temporal attribution sum:', sum(a['importance_score'] for a in temp_attr))
for a in temp_attr:
    print(' ', a['cycle_label'], ':', a['importance_score'])

# Physics verification on test set predictions
print()
print('=== PHYSICS VERIFICATION ===')
from app.core.physics import validate_profile_physics
violations = 0
for i in range(len(t_pred)):
    result = validate_profile_physics(t_pred[i], s_pred[i])
    if not result['is_gravitationally_stable']:
        violations += 1
print('Total test profiles:', len(t_pred))
print('Profiles with density inversions:', violations)
print('Violation rate:', violations/len(t_pred)*100, '%')