#!/usr/bin/env python
"""Train and benchmark persistence + gradient-boosting baselines.

Uses the identical sequence splits as train_model.py (stratified
domain-aware float-level splits, seed 42) on the canonical CSV, in
original physical units (trees need no scaling). Writes the
metrics_comparison rows to backend/app/ml/artifacts/baseline_metrics.json,
including the LSTM row re-evaluated from saved artifacts.
"""
import argparse
import json
import sys
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
from sklearn.model_selection import train_test_split

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.baselines import (
    persistence_predict,
    predict_gradient_boosting,
    profile_metrics,
    train_gradient_boosting,
)
from app.ml.model import PhysicsInformedBiLSTM

SEED = 42
STANDARD_DEPTHS = [5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]
TEMP_COLS = [f"temp_{d}" for d in STANDARD_DEPTHS]
SAL_COLS = [f"sal_{d}" for d in STANDARD_DEPTHS]
ARTIFACTS_DIR = Path(__file__).parent.parent / "app" / "ml" / "artifacts"


def build_windows(df: pd.DataFrame):
    """Same windowing as train_model.py: 3 input cycles -> 1 target (original units)."""
    Xs, yTs, ySs = [], [], []
    for _, g in df.sort_values(["wmo", "cycle"]).groupby("wmo"):
        g = g.dropna(subset=TEMP_COLS + SAL_COLS + ["cycle"]).reset_index(drop=True)
        if len(g) < 4:
            continue
        t = g[TEMP_COLS].to_numpy(dtype=np.float32)
        s = g[SAL_COLS].to_numpy(dtype=np.float32)
        for i in range(len(g) - 3):
            Xs.append(np.concatenate([t[i : i + 3], s[i : i + 3]], axis=1))
            yTs.append(t[i + 3])
            ySs.append(s[i + 3])
    return np.stack(Xs), np.stack(yTs), np.stack(ySs)


def main() -> None:
    parser = argparse.ArgumentParser(description="Train persistence + GB baselines")
    parser.add_argument("--csv", type=Path, default=Path(__file__).parent.parent / "data" / "processed" / "argo_30floats_canonical.csv")
    parser.add_argument("--seed", type=int, default=SEED)
    args = parser.parse_args()

    df = pd.read_csv(args.csv)
    df = df.dropna(subset=TEMP_COLS + SAL_COLS).reset_index(drop=True)
    phys = (
        (df[TEMP_COLS].ge(-2.0) & df[TEMP_COLS].le(35.0)).all(axis=1)
        & (df[SAL_COLS].ge(30.0) & df[SAL_COLS].le(42.0)).all(axis=1)
    )
    df = df[phys].reset_index(drop=True)

    # Identical stratified splits to train_model.py (seed 42, no leakage)
    ARCTIC_WMOS = {6903058, 6903059, 6903060, 6903062, 6903063}
    wmos = sorted(df["wmo"].unique().tolist())
    arctic = sorted(set(wmos) & ARCTIC_WMOS)
    arabian = sorted(set(wmos) - ARCTIC_WMOS)
    train_ar, rest_ar = train_test_split(arabian, test_size=10, random_state=args.seed)
    _, test_ar = train_test_split(rest_ar, test_size=5, random_state=args.seed)
    test_wmos = sorted(test_ar)
    print(f"Test floats ({len(test_wmos)}): {test_wmos}")

    test_df = df[df["wmo"].isin(test_wmos)].reset_index(drop=True)
    train_df = df[~df["wmo"].isin(test_wmos)].reset_index(drop=True)
    Xtr, yTtr, yStr = build_windows(train_df)
    Xte, yTte, ySte = build_windows(test_df)
    print(f"Windows: train={len(Xtr)} test={len(Xte)}")

    # 1. Persistence (t-1)
    pT, pS = persistence_predict(Xte)
    persistence_row = profile_metrics(yTte, ySte, pT, pS, "Persistence Baseline (t-1)")
    print("Persistence:", persistence_row)

    # 2. Gradient boosting (fit on train windows, original units)
    models = train_gradient_boosting(Xtr, yTtr, yStr, seed=args.seed)
    gT, gS = predict_gradient_boosting(models, Xte)
    gb_row = profile_metrics(yTte, ySte, gT, gS, "Gradient Boosting / Ridge")
    print("GradientBoost:", gb_row)

    # 3. LSTM row from saved artifacts (same test windows, via preprocessor)
    pre = joblib.load(ARTIFACTS_DIR / "preprocessor.joblib")
    ts, ss = pre["temp_scaler"], pre["sal_scaler"]
    model = PhysicsInformedBiLSTM()
    model.load_state_dict(torch.load(ARTIFACTS_DIR / "model_weights.pt", map_location="cpu"))
    model.eval()
    Xs = np.concatenate(
        [ts.transform(Xte[:, :, :16].reshape(-1, 16)).reshape(len(Xte), 3, 16),
         ss.transform(Xte[:, :, 16:].reshape(-1, 16)).reshape(len(Xte), 3, 16)],
        axis=2,
    ).astype(np.float32)
    with torch.no_grad():
        lT_scaled, lS_scaled = model(torch.as_tensor(Xs))
    lT = ts.inverse_transform(lT_scaled.numpy())
    lS = ss.inverse_transform(lS_scaled.numpy())
    lstm_row = profile_metrics(yTte, ySte, lT, lS, "FloatChat X-RAG (LSTM + MC Dropout)")
    print("LSTM:", lstm_row)

    rows = [persistence_row, gb_row, lstm_row]
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS_DIR / "baseline_metrics.json").write_text(json.dumps(rows, indent=2))
    print(f"Saved to {ARTIFACTS_DIR / 'baseline_metrics.json'}")


if __name__ == "__main__":
    main()
