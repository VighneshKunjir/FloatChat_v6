#!/usr/bin/env python
"""Train the Physics-Informed Bi-LSTM on Argo sequence splits.

Pipeline (per .ai/ml_spec.md and .ai/data_spec.md):
- Load canonical CSV (one row per profile, 16 T + 16 S levels).
- Float-level splits (seed 42, no leakage): train / val / test by WMO ID.
- Sliding windows of 4 consecutive cycles: 3 input -> 1 target.
- StandardScaler fitted on training profiles only.
- AdamW + cosine annealing, early stopping on val temp RMSE.
- Artifacts: model_weights.pt, preprocessor.joblib, metadata.json.

Device priority: cuda > mps > cpu.
"""
import argparse
import hashlib
import json
import random
import sys
import time
from datetime import date
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, Dataset

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.ml.loss import PhysicsConstrainedLoss
from app.ml.model import PhysicsInformedBiLSTM, get_device

SEED = 42
STANDARD_DEPTHS = [5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]
TEMP_COLS = [f"temp_{d}" for d in STANDARD_DEPTHS]
SAL_COLS = [f"sal_{d}" for d in STANDARD_DEPTHS]
ARTIFACTS_DIR = Path(__file__).parent.parent / "app" / "ml" / "artifacts"


def set_seed(seed: int = SEED) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return "sha256_" + h.hexdigest()[:12]


def build_windows(df: pd.DataFrame) -> tuple:
    """Build (X, yT, yS, meta) from sorted per-float profiles.

    X: (n, 3, 32) with [16T, 16S] per step; yT/yS: (n, 16).
    """
    Xs, yTs, ySs, metas = [], [], [], []
    for wmo, g in df.sort_values(["wmo", "cycle"]).groupby("wmo"):
        g = g.dropna(subset=TEMP_COLS + SAL_COLS + ["cycle"]).reset_index(drop=True)
        if len(g) < 4:
            continue
        t = g[TEMP_COLS].to_numpy(dtype=np.float32)
        s = g[SAL_COLS].to_numpy(dtype=np.float32)
        cyc = g["cycle"].to_numpy()
        for i in range(len(g) - 3):
            seq_t = t[i : i + 3]
            seq_s = s[i : i + 3]
            x = np.concatenate([seq_t, seq_s], axis=1)  # (3, 32)
            Xs.append(x)
            yTs.append(t[i + 3])
            ySs.append(s[i + 3])
            metas.append((int(wmo), int(cyc[i + 3])))
    if not Xs:
        raise ValueError("No training windows built; check dataset cycles per float.")
    return np.stack(Xs), np.stack(yTs), np.stack(ySs), metas


class SequenceDataset(Dataset):
    def __init__(self, X, yT, yS):
        self.X = torch.as_tensor(X, dtype=torch.float32)
        self.yT = torch.as_tensor(yT, dtype=torch.float32)
        self.yS = torch.as_tensor(yS, dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.yT[idx], self.yS[idx]


def rmse(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.sqrt(np.mean((a - b) ** 2)))


@torch.no_grad()
def evaluate(model, loader, device, temp_scaler, sal_scaler):
    model.eval()
    t_preds, t_trues, s_preds, s_trues = [], [], [], []
    for X, yT, yS in loader:
        X = X.to(device)
        pt, ps = model(X)
        t_preds.append(temp_scaler.inverse_transform(pt.cpu().numpy()))
        t_trues.append(temp_scaler.inverse_transform(yT.numpy()))
        s_preds.append(sal_scaler.inverse_transform(ps.cpu().numpy()))
        s_trues.append(sal_scaler.inverse_transform(yS.numpy()))
    t_pred = np.concatenate(t_preds)
    t_true = np.concatenate(t_trues)
    s_pred = np.concatenate(s_preds)
    s_true = np.concatenate(s_trues)
    # Thermocline indices for 50/75/100/150 dbar
    th_idx = [2, 3, 4, 5]
    return {
        "temp_rmse": rmse(t_pred, t_true),
        "sal_rmse": rmse(s_pred, s_true),
        "therm_rmse": rmse(t_pred[:, th_idx], t_true[:, th_idx]),
        "t_pred": t_pred,
        "t_true": t_true,
    }


def inversion_rate(t_pred: np.ndarray, s_pred: np.ndarray) -> float:
    """Fraction of predicted profiles with a density inversion (polynomial sigma)."""
    sigma = 28.14 - 0.0735 * t_pred - 0.00469 * t_pred**2 + 0.802 * (s_pred - 35.0)
    d = np.diff(sigma, axis=1)
    depths = np.array(STANDARD_DEPTHS, dtype=float)
    dz = np.diff(depths)
    viol = (d / dz) < -1e-6
    return float(viol.any(axis=1).mean())


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Physics-Informed Bi-LSTM")
    parser.add_argument("--csv", type=Path, default=Path(__file__).parent.parent / "data" / "processed" / "argo_30floats_canonical.csv")
    parser.add_argument("--epochs", type=int, default=60)
    parser.add_argument("--patience", type=int, default=15)
    parser.add_argument("--batch-size", type=int, default=None)
    parser.add_argument("--lr", type=float, default=1e-3)
    parser.add_argument("--weight-decay", type=float, default=1e-4)
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--basin-filter", action="store_true",
                        help="Restrict to Arabian Sea basin box (lat 6-26N, lon 53-79E per data_spec).")
    parser.add_argument("--split-mode", choices=["spatial", "temporal"], default="spatial",
                        help="spatial: float-level splits (unseen floats in val/test). "
                             "temporal: last-10-cycle windows per float held out as test "
                             "(operational forecast regime, per rules.md).")
    args = parser.parse_args()

    set_seed(args.seed)
    device = get_device()
    batch_size = args.batch_size or (32 if device.type == "cuda" else 16)
    use_amp = device.type == "cuda"

    df = pd.read_csv(args.csv)
    df = df.dropna(subset=TEMP_COLS + SAL_COLS).reset_index(drop=True)
    # Physical range cleaning per .ai/data_spec.md (fill sentinels / bad
    # interpolations slip through the NetCDF processor): T in [-2, 35] C,
    # S in [30, 42] PSU. Rows violating any level are dropped.
    n_raw = len(df)
    phys_mask = (
        (df[TEMP_COLS].ge(-2.0) & df[TEMP_COLS].le(35.0)).all(axis=1)
        & (df[SAL_COLS].ge(30.0) & df[SAL_COLS].le(42.0)).all(axis=1)
    )
    df = df[phys_mask].reset_index(drop=True)
    print(f"Physical-range filter: kept {len(df)}/{n_raw} profiles")
    if args.basin_filter:
        n_pre = len(df)
        df = df[(df["latitude"].ge(6.0) & df["latitude"].le(26.0))
                & (df["longitude"].ge(53.0) & df["longitude"].le(79.0))].reset_index(drop=True)
        print(f"Basin filter (6-26N, 53-79E): kept {len(df)}/{n_pre} profiles")
    # Stratified domain-aware spatial split (float-level, seed 42, no leakage):
    # sub-polar regime (Arctic 69030xx) is distributed across train/val so no
    # split is dominated by a single water mass; test stays all-Arabian
    # (operational scope per PRD).
    ARCTIC_WMOS = {6903058, 6903059, 6903060, 6903062, 6903063}
    split_desc = ""
    if args.split_mode == "spatial":
        wmos = sorted(df["wmo"].unique().tolist())
        arctic = sorted(set(wmos) & ARCTIC_WMOS)
        arabian = sorted(set(wmos) - ARCTIC_WMOS)
        train_ar, rest_ar = train_test_split(arabian, test_size=10, random_state=args.seed)
        val_ar, test_ar = train_test_split(rest_ar, test_size=5, random_state=args.seed)
        train_ac = arctic[:-1] if len(arctic) > 1 else arctic
        val_ac = arctic[-1:] if len(arctic) > 1 else []
        train_wmos = sorted(train_ar + train_ac)
        val_wmos = sorted(val_ar + val_ac)
        test_wmos = sorted(test_ar)
        print(f"Floats: train={len(train_wmos)} val={len(val_wmos)} test={len(test_wmos)}")
        print(f"  Arctic dist: train={sorted(set(train_wmos) & ARCTIC_WMOS)} "
              f"val={sorted(set(val_wmos) & ARCTIC_WMOS)} test={sorted(set(test_wmos) & ARCTIC_WMOS)}")

        train_df = df[df["wmo"].isin(train_wmos)].reset_index(drop=True)
        val_df = df[df["wmo"].isin(val_wmos)].reset_index(drop=True)
        test_df = df[df["wmo"].isin(test_wmos)].reset_index(drop=True)

        # Fit scalers on training profiles only (no leakage)
        temp_scaler = StandardScaler().fit(train_df[TEMP_COLS].to_numpy(dtype=np.float64))
        sal_scaler = StandardScaler().fit(train_df[SAL_COLS].to_numpy(dtype=np.float64))

        def scale_frame(frame: pd.DataFrame):
            t = temp_scaler.transform(frame[TEMP_COLS].to_numpy(dtype=np.float64)).astype(np.float32)
            s = sal_scaler.transform(frame[SAL_COLS].to_numpy(dtype=np.float64)).astype(np.float32)
            out = frame.copy()
            out[TEMP_COLS] = t
            out[SAL_COLS] = s
            return out

        Xtr, yTtr, yStr, _ = build_windows(scale_frame(train_df))
        Xva, yTva, ySva, _ = build_windows(scale_frame(val_df))
        Xte, yTte, ySte, test_metas = build_windows(scale_frame(test_df))
        print(f"Windows: train={len(Xtr)} val={len(Xva)} test={len(Xte)}")
        split_desc = "stratified-domain float-level (arctic vs arabian), seed 42"
    else:
        # Temporal split: last-10-cycle windows per float -> test (operational
        # forecast regime per rules.md); remaining windows split train/val by
        # float. Scalers fit on non-test pool profiles only (no leakage).
        last10: dict = {}
        for wmo, g in df.groupby("wmo"):
            cyc = sorted(g["cycle"].dropna().unique().tolist())
            last10[int(wmo)] = set(cyc[-10:])
        is_test_row = df.apply(
            lambda r: int(r["cycle"]) in last10.get(int(r["wmo"]), set()), axis=1
        )
        pool_df = df[~is_test_row].reset_index(drop=True)
        temp_scaler = StandardScaler().fit(pool_df[TEMP_COLS].to_numpy(dtype=np.float64))
        sal_scaler = StandardScaler().fit(pool_df[SAL_COLS].to_numpy(dtype=np.float64))

        def scale_frame(frame: pd.DataFrame):
            t = temp_scaler.transform(frame[TEMP_COLS].to_numpy(dtype=np.float64)).astype(np.float32)
            s = sal_scaler.transform(frame[SAL_COLS].to_numpy(dtype=np.float64)).astype(np.float32)
            out = frame.copy()
            out[TEMP_COLS] = t
            out[SAL_COLS] = s
            return out

        Xal, yTal, ySal, metas = build_windows(scale_frame(df))
        metas_arr = np.array(metas, dtype=int)  # (n, 2): wmo, target cycle
        test_mask = np.array([
            int(c) in last10.get(int(w), set()) for w, c in metas_arr
        ])
        Xte, yTte, ySte = Xal[test_mask], yTal[test_mask], ySal[test_mask]
        Xpool, yTpool, ySpool = Xal[~test_mask], yTal[~test_mask], ySal[~test_mask]
        pool_wmos = sorted(set(int(w) for w in metas_arr[~test_mask][:, 0]))
        pool_arctic = sorted(set(pool_wmos) & ARCTIC_WMOS)
        pool_arabian = sorted(set(pool_wmos) - ARCTIC_WMOS)
        train_ar, val_ar = train_test_split(pool_arabian, test_size=5, random_state=args.seed)
        val_ac = pool_arctic[-1:] if pool_arctic else []
        train_ac = [w for w in pool_arctic if w not in val_ac]
        train_wmos = sorted(train_ar + train_ac)
        val_wmos = sorted(val_ar + val_ac)
        test_wmos = sorted(set(int(w) for w in metas_arr[test_mask][:, 0]))
        tr_mask = np.array([int(w) in set(train_wmos) for w in metas_arr[~test_mask][:, 0]])
        Xtr, yTtr, yStr = Xpool[tr_mask], yTpool[tr_mask], ySpool[tr_mask]
        Xva, yTva, ySva = Xpool[~tr_mask], yTpool[~tr_mask], ySpool[~tr_mask]
        test_metas = [tuple(m) for m in metas_arr[test_mask].tolist()]
        print(f"Windows: train={len(Xtr)} val={len(Xva)} test={len(Xte)} "
              f"(last-10-cycle holdout, {len(test_wmos)} floats in test)")
        print(f"  Arctic dist: train={sorted(set(train_wmos) & ARCTIC_WMOS)} "
              f"val={sorted(set(val_wmos) & ARCTIC_WMOS)}")
        split_desc = "temporal last-10-cycle holdout (test), float-level train/val, seed 42"

    train_loader = DataLoader(SequenceDataset(Xtr, yTtr, yStr), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(SequenceDataset(Xva, yTva, ySva), batch_size=batch_size)
    test_loader = DataLoader(SequenceDataset(Xte, yTte, ySte), batch_size=batch_size)

    model = PhysicsInformedBiLSTM().to(device)
    # Physics terms operate in original units: hand the loss the
    # StandardScaler stats so it denormalizes predictions first.
    criterion = PhysicsConstrainedLoss(
        temp_mean=temp_scaler.mean_,
        temp_std=temp_scaler.scale_,
        sal_mean=sal_scaler.mean_,
        sal_std=sal_scaler.scale_,
    ).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=args.weight_decay)
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=100, eta_min=1e-6)
    scaler = torch.cuda.amp.GradScaler() if use_amp else None

    best_rmse = float("inf")
    best_state = None
    bad_epochs = 0
    start = time.time()

    for epoch in range(1, args.epochs + 1):
        model.train()
        tot = 0.0
        for X, yT, yS in train_loader:
            X, yT, yS = X.to(device), yT.to(device), yS.to(device)
            optimizer.zero_grad()
            if use_amp:
                with torch.cuda.amp.autocast():
                    pt, ps = model(X)
                    loss, _ = criterion(pt, yT, ps, yS)
                scaler.scale(loss).backward()
                scaler.step(optimizer)
                scaler.update()
            else:
                pt, ps = model(X)
                loss, _ = criterion(pt, yT, ps, yS)
                loss.backward()
                optimizer.step()
            tot += loss.item() * len(X)
        scheduler.step()

        val = evaluate(model, val_loader, device, temp_scaler, sal_scaler)
        print(f"epoch {epoch:3d} train_loss={tot/len(Xtr):.4f} val_temp_rmse={val['temp_rmse']:.4f} val_sal_rmse={val['sal_rmse']:.4f}")

        if val["temp_rmse"] < best_rmse - 1e-6:
            best_rmse = val["temp_rmse"]
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}
            bad_epochs = 0
        else:
            bad_epochs += 1
            if bad_epochs >= args.patience:
                print(f"Early stopping at epoch {epoch} (patience {args.patience})")
                break

    elapsed = time.time() - start
    if best_state is not None:
        model.load_state_dict(best_state)

    test = evaluate(model, test_loader, device, temp_scaler, sal_scaler)
    # Inversion rate on test predictions (original units)
    model.eval()
    s_preds = []
    with torch.no_grad():
        for X, _, _ in test_loader:
            _, ps = model(X.to(device))
            s_preds.append(sal_scaler.inverse_transform(ps.cpu().numpy()))
    s_pred = np.concatenate(s_preds)
    inv_rate = inversion_rate(test["t_pred"], s_pred)

    print(f"Test temp RMSE: {test['temp_rmse']:.4f} C | sal RMSE: {test['sal_rmse']:.4f} PSU | therm RMSE: {test['therm_rmse']:.4f} C")
    print(f"Inversion rate: {inv_rate*100:.3f}% | elapsed: {elapsed:.1f}s on {device}")

    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    torch.save(model.state_dict(), ARTIFACTS_DIR / "model_weights.pt")
    joblib.dump(
        {"temp_scaler": temp_scaler, "sal_scaler": sal_scaler, "standard_depths": STANDARD_DEPTHS},
        ARTIFACTS_DIR / "preprocessor.joblib",
    )
    metadata = {
        "model_version": "v1.2.0-bilstm-teos10",
        "training_date": date.today().isoformat(),
        "dataset_hash": sha256_of_file(args.csv),
        "device": str(device),
        "split": split_desc,
        "arctic_wmos": sorted(ARCTIC_WMOS),
        "train_floats": sorted(int(w) for w in train_wmos),
        "val_floats": sorted(int(w) for w in val_wmos),
        "test_floats": sorted(int(w) for w in test_wmos),
        "validation_rmse_temp": round(float(best_rmse), 4),
        "test_rmse_temp": round(float(test["temp_rmse"]), 4),
        "test_rmse_sal": round(float(test["sal_rmse"]), 4),
        "test_thermocline_rmse": round(float(test["therm_rmse"]), 4),
        "test_inversion_rate": round(float(inv_rate), 5),
        "elapsed_s": round(float(elapsed), 1),
    }
    (ARTIFACTS_DIR / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(f"Artifacts saved to {ARTIFACTS_DIR}")


if __name__ == "__main__":
    main()
