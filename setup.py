#!/usr/bin/env python
"""FloatChat one-command setup, data, training, and serve orchestrator.

Profiles:
  full    First-time setup: env -> deps -> download -> process -> db
          -> train -> baselines -> serve.
  serve   Daily dev: verify env/deps, refresh db (cheap), launch servers.
          Heavy stages (download/process/train/baselines) are skipped
          unless explicitly forced or requested.

Flags refine any profile: --only, --skip, --force[-download|-process|-train],
--floats/--floats-file/--discover (data volume), --no-serve, --check.

Examples:
  python setup.py --profile full
  python setup.py --profile serve
  python setup.py --profile full --skip-train
  python setup.py --discover --years 2020-2024 --min-cycles 50
  python setup.py --only db
  python setup.py --check
"""
import argparse
import os
import shutil
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).parent.resolve()
BACKEND = ROOT / "backend"
RAW_DIR = BACKEND / "data" / "raw"
CSV_PATH = BACKEND / "data" / "processed" / "argo_30floats_canonical.csv"
ARTIFACTS = BACKEND / "app" / "ml" / "artifacts"
DB_PATH = BACKEND / "data" / "floatchat.db"

STEPS = ["env", "deps", "download", "process", "db", "train", "baselines", "serve"]
HEAVY = {"download", "process", "train", "baselines"}


def log(msg: str) -> None:
    print(f"[setup] {msg}", flush=True)


def venv_python() -> Path:
    candidate = ROOT / "venv" / "Scripts" / "python.exe"
    if candidate.exists():
        return candidate
    candidate = ROOT / "venv" / "bin" / "python"
    if candidate.exists():
        return candidate
    return Path(sys.executable)


def run(cmd, cwd=None, env=None, check=True):
    printable = " ".join(str(c) for c in cmd)
    log(f"$ {printable}")
    result = subprocess.run(cmd, cwd=cwd or ROOT, env=env)
    if check and result.returncode != 0:
        raise SystemExit(f"FAILED ({result.returncode}): {printable}")
    return result.returncode


def newest_mtime(path: Path) -> float:
    try:
        if path.is_file():
            return path.stat().st_mtime
    except OSError:
        return 0.0
    latest = 0.0
    for p in path.rglob("*"):
        if p.is_file():
            try:
                latest = max(latest, p.stat().st_mtime)
            except OSError:
                pass
    return latest


# ---------------------------------------------------------------- steps

def step_env(args) -> None:
    example = ROOT / ".env.example"
    target = ROOT / ".env"
    if not target.exists():
        if example.exists():
            shutil.copy(example, target)
            log("created .env from .env.example")
        else:
            target.write_text("GEMINI_API_KEY=\n")
            log("created minimal .env (no .env.example found)")
    text = target.read_text()
    if "GEMINI_API_KEY" not in text:
        text += "\nGEMINI_API_KEY=\n"
        target.write_text(text)
    if args.profile == "full" and sys.stdin.isatty():
        for line in text.splitlines():
            if line.startswith("GEMINI_API_KEY=") and not line.split("=", 1)[1].strip():
                key = input("GEMINI_API_KEY (Enter to skip, offline fallback stays active): ").strip()
                if key:
                    target.write_text(text.replace("GEMINI_API_KEY=", f"GEMINI_API_KEY={key}", 1))
                    log("stored GEMINI_API_KEY in .env")
                else:
                    log("skipped (offline synthesis fallback stays active)")
                break


def step_deps(args) -> None:
    venv = ROOT / "venv"
    if not venv.exists():
        log("creating virtualenv ./venv ...")
        run([sys.executable, "-m", "venv", "venv"])
    py = venv_python()
    probe = subprocess.run(
        [str(py), "-c", "import fastapi, torch, sqlalchemy, sklearn"],
        capture_output=True,
    )
    if probe.returncode != 0:
        log("installing backend requirements ...")
        run([str(py), "-m", "pip", "install", "-r", "backend/requirements.txt"])
    else:
        log("backend deps OK (fastapi/torch/sqlalchemy/sklearn import)")
    if not (ROOT / "node_modules").exists():
        log("running npm install ...")
        run(["cmd", "/c", "npm", "install"])
    else:
        log("node_modules present, skipping npm install")


def step_download(args) -> None:
    script = BACKEND / "scripts" / "download_argo_netcdf.py"
    cmd = [str(venv_python()), str(script), "--output", str(RAW_DIR)]
    if args.floats_file:
        cmd += ["--floats-file", str(args.floats_file), "--all"]
    elif args.floats:
        cmd += ["--float", args.floats]
    elif args.discover:
        out = Path(args.floats_file) if args.floats_file else BACKEND / "data" / "floats.custom.txt"
        disc = [str(venv_python()), str(BACKEND / "scripts" / "discover_arabian_sea_floats.py"),
                "--top-n", str(args.top_n), "--output", str(out)]
        if args.years:
            disc += ["--years", args.years]
        if args.min_cycles:
            disc += ["--min-cycles", str(args.min_cycles)]
        run(disc)
        cmd += ["--floats-file", str(out), "--all"]
    else:
        cmd += ["--all"]
    run(cmd)


def step_process(args) -> None:
    run([str(venv_python()), str(BACKEND / "scripts" / "process_argo_netcdf.py")])


def step_db(args) -> None:
    run([str(venv_python()), "-m", "alembic", "upgrade", "head"], cwd=BACKEND)
    run([str(venv_python()), str(BACKEND / "scripts" / "seed_all_floats.py")])


def step_train(args) -> None:
    cmd = [str(venv_python()), str(BACKEND / "scripts" / "train_model.py"),
           "--epochs", str(args.train_epochs), "--patience", str(args.train_patience)]
    if args.split_mode != "spatial":
        cmd += ["--split-mode", args.split_mode]
    run(cmd)


def step_baselines(args) -> None:
    run([str(venv_python()), str(BACKEND / "scripts" / "train_baselines.py")])


# ---------------------------------------------------------------- freshness

def is_fresh(step: str, args) -> tuple:
    """Return (fresh: bool, reason: str). Never fresh when forced."""
    if step == "download":
        if args.force_download or args.force or args.floats or args.floats_file or args.discover:
            return False, "explicitly requested"
        floats = [d for d in RAW_DIR.iterdir()] if RAW_DIR.exists() else []
        floats = [d for d in floats if d.is_dir()]
        if len(floats) >= 1:
            return True, f"{len(floats)} float dirs present"
        return False, "raw store empty"
    if step == "process":
        if args.force_process or args.force:
            return False, "forced"
        if CSV_PATH.exists() and CSV_PATH.stat().st_size > 0:
            if RAW_DIR.exists() and newest_mtime(CSV_PATH) > newest_mtime(RAW_DIR):
                return True, "CSV newer than raw store"
            if not RAW_DIR.exists() or not any(RAW_DIR.iterdir()):
                return True, "CSV present"
        return False, "CSV missing or stale"
    if step == "train":
        if args.force_train or args.force:
            return False, "forced"
        need = ["model_weights.pt", "preprocessor.joblib", "metadata.json"]
        if all((ARTIFACTS / f).exists() for f in need):
            return True, "artifacts present"
        return False, "artifacts missing"
    if step == "baselines":
        if args.force_train or args.force:
            return False, "forced (train)"
        if (ARTIFACTS / "baseline_metrics.json").exists():
            return True, "baseline_metrics.json present"
        return False, "baseline_metrics.json missing"
    return False, ""


# ---------------------------------------------------------------- serve

def _pump(proc, tag: str) -> None:
    for line in proc.stdout:
        print(f"[{tag}] {line}", end="", flush=True)


def wait_for(url: str, timeout: int, label: str) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=5) as r:
                if r.status < 500:
                    return True
        except Exception:
            time.sleep(2)
    print(f"[setup] WARNING: {label} not reachable at {url}")
    return False


def step_serve(args) -> None:
    py = str(venv_python())
    env = dict(os.environ, USE_PYTHON_BACKEND="true")
    api = subprocess.Popen(
        [py, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", "8000", "--app-dir", "backend"],
        cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
    )
    threading.Thread(target=_pump, args=(api, "api"), daemon=True).start()
    if not wait_for("http://127.0.0.1:8000/api/health", 90, "FastAPI"):
        api.terminate()
        raise SystemExit("backend failed to start; see [api] log above")
    log("backend healthy at http://127.0.0.1:8000")
    ui = subprocess.Popen(
        ["cmd", "/c", "npm", "run", "dev"], cwd=ROOT,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env,
    )
    threading.Thread(target=_pump, args=(ui, "ui"), daemon=True).start()
    wait_for("http://localhost:3000/", 120, "frontend")
    log("FloatChat live at http://localhost:3000  (Ctrl+C stops both servers)")
    try:
        while True:
            if api.poll() is not None or ui.poll() is not None:
                raise SystemExit("a server exited; see log above")
            time.sleep(1)
    except KeyboardInterrupt:
        log("stopping servers ...")
    finally:
        for proc in (ui, api):
            try:
                proc.terminate()
            except Exception:
                pass


STEP_FNS = {
    "env": step_env,
    "deps": step_deps,
    "download": step_download,
    "process": step_process,
    "db": step_db,
    "train": step_train,
    "baselines": step_baselines,
    "serve": step_serve,
}


def check_status() -> int:
    class A:  # minimal namespace for freshness probes
        force = force_download = force_process = force_train = False
        floats = floats_file = discover = None
    a = A()
    print(f"{'step':<10} {'status':<8} detail")
    missing = 0
    for step in STEPS:
        if step == "serve":
            print(f"{'serve':<10} {'manual':<8} run setup.py --profile serve")
            continue
        if step in ("env", "deps", "db"):
            print(f"{step:<10} {'run':<8} cheap/always (use --skip to omit)")
            continue
        fresh, reason = is_fresh(step, a)
        print(f"{step:<10} {'fresh' if fresh else 'MISSING':<8} {reason}")
        missing += 0 if fresh else 1
    return 1 if missing else 0


def main() -> None:
    p = argparse.ArgumentParser(description="FloatChat setup / data / train / serve orchestrator")
    p.add_argument("--profile", choices=["full", "serve"], default="full")
    p.add_argument("--only", nargs="+", choices=STEPS, default=None)
    p.add_argument("--skip", nargs="+", choices=STEPS, default=[])
    p.add_argument("--force", action="store_true")
    p.add_argument("--force-download", action="store_true")
    p.add_argument("--force-process", action="store_true")
    p.add_argument("--force-train", action="store_true")
    p.add_argument("--floats", default=None, help="WMO IDs, comma-separated")
    p.add_argument("--floats-file", default=None)
    p.add_argument("--discover", action="store_true")
    p.add_argument("--years", default=None, help="e.g. '2020-2024'")
    p.add_argument("--min-cycles", type=int, default=0)
    p.add_argument("--top-n", type=int, default=200)
    p.add_argument("--train-epochs", type=int, default=60)
    p.add_argument("--train-patience", type=int, default=15)
    p.add_argument("--split-mode", default="spatial", choices=["spatial", "temporal"])
    p.add_argument("--no-serve", action="store_true")
    p.add_argument("--check", action="store_true")
    args = p.parse_args()

    if args.check:
        raise SystemExit(check_status())

    if args.only:
        steps = [s for s in STEPS if s in args.only]
    elif args.profile == "serve":
        steps = ["env", "deps", "db", "serve"]
    else:
        steps = list(STEPS)
    steps = [s for s in steps if s not in set(args.skip or [])]
    if args.no_serve and "serve" in steps:
        steps.remove("serve")

    log(f"profile={args.profile} steps={steps}")
    for step in steps:
        if step in HEAVY and step not in (args.only or []) and args.profile == "serve":
            continue  # serve profile never runs heavy stages implicitly
        if step in ("download", "process", "train", "baselines"):
            fresh, reason = is_fresh(step, args)
            if fresh:
                log(f"skip {step} ({reason}); use --force-{step} to redo")
                continue
        log(f"--- step: {step} ---")
        STEP_FNS[step](args)
    log("done")


if __name__ == "__main__":
    main()
