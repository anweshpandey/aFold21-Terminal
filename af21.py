#!/usr/bin/env python3
"""Terminal front-end for AlphaFold2/ColabFold on a persistent Google Colab runtime."""
from __future__ import annotations
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import zipfile

APP_DIR = Path.home() / ".local" / "share" / "alphafold21"
SESSION = os.environ.get("AF21_SESSION", "alphafold21")
AUTH = os.environ.get("AF21_AUTH", "oauth2")
REMOTE_ROOT = "/content/af21_runs"
REMOTE_CACHE = "/content/af21_cache"
VALID_AA = set("ACDEFGHIKLMNPQRSTVWYXUO")


def run_cmd(args, *, check=True, capture=False, timeout=None):
    cmd = ["colab", f"--auth={AUTH}", *map(str, args)]
    print("\n$ " + " ".join(cmd), flush=True)
    return subprocess.run(cmd, check=check, text=True,
                          stdout=subprocess.PIPE if capture else None,
                          stderr=subprocess.PIPE if capture else None,
                          timeout=timeout)


def colab_available():
    if shutil.which("colab") is None:
        print("ERROR: 'colab' CLI was not found. Re-run install.sh or activate the alphafold21 environment.", file=sys.stderr)
        return False
    return True


def session_status():
    return run_cmd(["status", "-s", SESSION], check=False, capture=True)


def ensure_session(gpu="T4"):
    status = session_status()
    output = (status.stdout or "") + "\n" + (status.stderr or "")
    output_lower = output.lower()
    missing = (
        f"session '{SESSION.lower()}' not found" in output_lower
        or f'session "{SESSION.lower()}" not found' in output_lower
    )

    if status.returncode == 0 and not missing:
        print(f"\nReusing existing Colab session '{SESSION}'.")
        if output.strip():
            print(output.strip())
        return 0

    print(f"\nColab session '{SESSION}' was not found or is unavailable.")
    print("Create it with this command:")
    print(f"colab --auth={AUTH} new -s {SESSION} --gpu {gpu}")
    try:
        answer = input("Create a new GPU session now? [Y/n]: ").strip().lower()
    except EOFError:
        # Batch mode may not have an interactive stdin prompt; accept the default.
        answer = ""

    if answer not in ("", "y", "yes"):
        print("Session creation cancelled.")
        raise RuntimeError("Colab session is unavailable; no prediction was started.")

    created = run_cmd(["new", "-s", SESSION, "--gpu", gpu], check=False)
    if created.returncode != 0:
        raise RuntimeError(
            f"Could not create Colab session '{SESSION}'. Check the CLI output above."
        )
    print(f"Colab session '{SESSION}' created and ready to use.")
    return 0


def prompt_sequences():
    print("Enter a protein sequence. For a multimer, separate chain sequences with ':'")
    print("Example: MKT... or CHAIN_A_SEQUENCE:CHAIN_B_SEQUENCE")
    raw = input("Protein sequence(s): ").strip()
    # If FASTA starts with a header, keep reading lines until a blank line so multi-record FASTA can be pasted.
    if raw.startswith(">"):
        fasta_lines = [raw]
        print("Paste the remaining FASTA lines; press Enter on an empty line when finished.")
        while True:
            try:
                line = input()
            except EOFError:
                break
            if not line.strip():
                break
            fasta_lines.append(line.strip())
        raw = "\n".join(fasta_lines)
    # Accept FASTA pasted on one or several lines, and remove whitespace.
    if raw.startswith(">") or "\n>" in raw:
        chunks, current = [], []
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            if line.startswith(">"):
                if current:
                    chunks.append("".join(current))
                    current = []
            else:
                current.append(line)
        if current:
            chunks.append("".join(current))
        seqs = chunks
    else:
        seqs = [re.sub(r"\s+", "", part).upper() for part in raw.split(":")]
    seqs = [re.sub(r"\s+", "", s).upper() for s in seqs if s.strip()]
    if not seqs:
        raise ValueError("No sequence was provided.")
    for i, seq in enumerate(seqs, 1):
        bad = sorted(set(seq) - VALID_AA)
        if bad:
            raise ValueError(f"Chain {i} contains unsupported character(s): {''.join(bad)}")
        if len(seq) < 1:
            raise ValueError(f"Chain {i} is empty.")
    total = sum(map(len, seqs))
    if total > 1000:
        print(f"WARNING: total length is {total} residues; runtime memory/limits may be insufficient.")
    print(f"Validated {len(seqs)} chain(s), {total} total residues.")
    return seqs


def prompt_output_dir():
    raw = input("Results directory [./af21_results]: ").strip() or "./af21_results"
    path = Path(raw).expanduser().resolve()
    if path.exists() and any(path.iterdir()):
        answer = input(f"Directory '{path}' already exists and is not empty. Continue and keep existing files? [y/N]: ").strip().lower()
        if answer not in {"y", "yes"}:
            raise ValueError("Cancelled to avoid mixing results. Enter a new output directory.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def remote_worker_text(config_path: str) -> str:
    # This code executes in the Colab kernel through `colab exec`.
    return r'''#!/usr/bin/env python3
import csv, json, os, shutil, sys, traceback, zipfile
from pathlib import Path
import matplotlib
matplotlib.use("Agg")

CONFIG_PATH = __CONFIG_PATH__
with open(CONFIG_PATH, encoding="utf-8") as f:
    cfg = json.load(f)

outdir = Path(cfg["remote_outdir"])
cache = Path(cfg["remote_cache"])
outdir.mkdir(parents=True, exist_ok=True)
cache.mkdir(parents=True, exist_ok=True)
seqs = cfg["sequences"]
job = cfg["job_name"]

fasta = outdir / "query.fasta"
with fasta.open("w", encoding="utf-8") as f:
    for i, seq in enumerate(seqs, 1):
        f.write(f">chain_{i}\n{seq}\n")
query_csv = outdir / f"{job}.csv"
with query_csv.open("w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["id", "sequence"])
    writer.writerow([job, ":".join(seqs)])

print("AlphaFold2/ColabFold remote worker")
print("Total residues:", sum(len(s) for s in seqs))
print("Chains:", len(seqs))
try:
    import subprocess
    import colabfold
except ImportError:
    print("ColabFold package is missing; installing it into this Colab runtime...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "colabfold[alphafold-minus-jax]==1.6.3"])

import logging, warnings
warnings.filterwarnings("ignore", category=FutureWarning)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
try:
    import subprocess
    gpu = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True, capture_output=True)
    print("GPU:", gpu.stdout.strip() if gpu.returncode == 0 else "No NVIDIA GPU reported")
except Exception:
    pass

from colabfold.batch import get_queries, set_model_type, run
from colabfold.download import download_alphafold_params
from colabfold import utils
try:
    if not getattr(utils, "setup_logging_done", False):
        utils.setup_logging(outdir / "colabfold.log")
        utils.setup_logging_done = True
except Exception as e:
    print("Note: could not configure ColabFold file logging:", e)

queries, is_complex = get_queries(str(query_csv))
model_type = set_model_type(is_complex, cfg.get("model_type", "auto"))
print("Model type:", model_type)
print("Downloading/checking model parameters in persistent runtime cache...")
download_alphafold_params(model_type, cache)

# Plotting callbacks are best-effort: a plotting issue must not invalidate a prediction.
def msa_callback(features, dpi=160):
    try:
        import matplotlib.pyplot as plt
        from colabfold.plot import plot_msa_v2
        plot_msa_v2(features, dpi=dpi)
        fig = plt.gcf()
        if fig and fig.axes:
            fig.savefig(outdir / "msa.png", dpi=dpi, bbox_inches="tight")
        plt.close("all")
    except Exception as exc:
        print("MSA plot skipped:", repr(exc))

def prediction_callback(unrelaxed_protein, query_sequence_len_array, prediction_result, input_features, prediction_kind):
    try:
        import matplotlib.pyplot as plt
        import numpy as np
        from colabfold import colabfold as cf
        positions = np.asarray(unrelaxed_protein.atom_positions[:, 1, :])
        plddt = np.asarray(unrelaxed_protein.b_factors[:, 0])
        multimer = len(query_sequence_len_array) > 1
        fig, axes = plt.subplots(1, 3 if multimer else 2, figsize=(12, 4), dpi=140)
        cf.plot_protein_backbone(protein=unrelaxed_protein, pos=positions, plddt=plddt,
                                 axes=axes[0], coloring="plddt", Ls=query_sequence_len_array if multimer else None)
        axes[0].set_title("Colored by pLDDT")
        cf.plot_pae(prediction_result["predicted_aligned_error"], axes[1],
                    Ls=query_sequence_len_array, colorkey_size=0.9)
        axes[1].set_title("Predicted aligned error")
        if multimer:
            cf.plot_protein_backbone(protein=unrelaxed_protein, pos=positions, plddt=plddt,
                                     axes=axes[2], coloring="chain", Ls=query_sequence_len_array)
            axes[2].set_title("Colored by chain")
        fig.tight_layout()
        fig.savefig(outdir / ("prediction_" + str(prediction_kind).replace("/", "_") + ".png"), dpi=160)
        plt.close(fig)
    except Exception as exc:
        print("Prediction plot skipped:", repr(exc))

print("Starting structure prediction...")
run(queries=queries,
    result_dir=str(outdir),
    use_templates=bool(cfg.get("use_templates", False)),
    custom_template_path=None,
    use_amber=bool(cfg.get("energy_minimize", False)),
    msa_mode=cfg.get("msa_mode", "mmseqs2_uniref_env"),
    model_type=model_type,
    num_models=5,
    num_recycles=int(cfg.get("num_recycles", 3)),
    model_order=[1, 2, 3, 4, 5],
    is_complex=is_complex,
    data_dir=cache,
    keep_existing_results=False,
    recompile_padding=1.0,
    rank_by="auto",
    pair_mode=cfg.get("pair_mode", "unpaired+paired"),
    stop_at_score=100.0,
    feature_dict_callback=msa_callback,
    prediction_callback=prediction_callback,
    dpi=160,
    user_agent="AlphaFold21-terminal-tool")

# Save metadata before organizing the raw ColabFold output.
(outdir / "run_metadata.json").write_text(json.dumps({
    "job_name": job, "sequences": seqs, "chain_count": len(seqs),
    "total_residues": sum(map(len, seqs)), "model_type": model_type,
    "msa_mode": cfg.get("msa_mode"), "num_recycles": cfg.get("num_recycles"),
    "energy_minimize": cfg.get("energy_minimize"), "use_templates": cfg.get("use_templates"),
    "remote_output_directory": str(outdir)
}, indent=2), encoding="utf-8")

# Create a predictable folder layout. ColabFold writes files to the run root;
# move them into subfolders before creating the downloadable archive.
folders = {
    "structures": outdir / "structures",
    "confidence": outdir / "confidence",
    "plots": outdir / "plots",
    "msa": outdir / "msa",
    "inputs": outdir / "inputs",
    "logs": outdir / "logs",
    "metadata": outdir / "metadata",
}
for folder in folders.values():
    folder.mkdir(parents=True, exist_ok=True)

relax = "relaxed" if cfg.get("energy_minimize", False) else "unrelaxed"
pdbs = sorted(outdir.glob(f"*_{relax}_rank_001_*.pdb"))
score_jsons = sorted(outdir.glob("*_scores_rank_001_*.json"))
if pdbs:
    shutil.copy2(pdbs[0], outdir / "best_model.pdb")
if score_jsons:
    shutil.copy2(score_jsons[0], outdir / "best_model_pae.json")

# Keep a copy of the selected best structure and score file in the obvious folders.
if (outdir / "best_model.pdb").exists():
    shutil.copy2(outdir / "best_model.pdb", folders["structures"] / "best_model.pdb")
if (outdir / "best_model_pae.json").exists():
    shutil.copy2(outdir / "best_model_pae.json", folders["confidence"] / "best_model_pae.json")

for p in list(outdir.iterdir()):
    if not p.is_file():
        continue
    name = p.name.lower()
    if p.suffix.lower() in {".pdb", ".cif", ".mmcif"}:
        dest = folders["structures"]
    elif p.suffix.lower() == ".png":
        dest = folders["plots"]
    elif p.suffix.lower() == ".a3m":
        dest = folders["msa"]
    elif p.name == "query.fasta":
        dest = folders["inputs"]
    elif p.suffix.lower() == ".csv":
        dest = folders["inputs"]
    elif p.name == "run_metadata.json":
        dest = folders["metadata"]
    elif p.suffix.lower() == ".json":
        dest = folders["confidence"]
    elif p.suffix.lower() in {".log", ".txt", ".bibtex"} or "log" in name:
        dest = folders["logs"] if p.suffix.lower() in {".log", ".txt"} else folders["metadata"]
    else:
        dest = folders["metadata"]
    target = dest / p.name
    # If an alias already exists in the destination, keep the copy already made.
    if target.exists():
        p.unlink()
    else:
        shutil.move(str(p), str(target))

# Put a short README at the top level so the user knows where to find things.
readme = outdir / "README_results.txt"
readme.write_text(
    "AlphaFold2/ColabFold prediction results\n"
    "=======================================\n\n"
    "structures/  Predicted PDB/mmCIF files; best_model.pdb is the top-ranked model.\n"
    "confidence/  Per-model score JSON files and best_model_pae.json.\n"
    "plots/       MSA, pLDDT, PAE and chain-coloured plots (when generated).\n"
    "msa/         Multiple-sequence-alignment files (when generated).\n"
    "inputs/      Input FASTA and ColabFold query CSV.\n"
    "logs/        Prediction and runtime logs.\n"
    "metadata/    Run settings and metadata.\n\n"
    "Interpret confidence metrics in the context of the biological system; "
    "prediction scores do not by themselves validate a structure experimentally.\n",
    encoding="utf-8"
)

archive = Path(cfg["remote_zip"])
archive.parent.mkdir(parents=True, exist_ok=True)
with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as zf:
    for p in outdir.rglob("*"):
        if p.is_file() and p != archive:
            zf.write(p, p.relative_to(outdir))
print("PREDICTION_COMPLETE")
print("Output directory:", outdir)
print("Archive:", archive)
'''.replace("__CONFIG_PATH__", repr(config_path))


def run_prediction(args):
    if not colab_available():
        return 2
    try:
        sequences = prompt_sequences()
        output_dir = prompt_output_dir()
    except (ValueError, KeyboardInterrupt) as exc:
        print(f"\nCancelled: {exc}", file=sys.stderr)
        return 2

    gpu = args.gpu.upper()
    if gpu not in {"T4", "L4", "A100", "H100", "G4"}:
        print("Unsupported GPU choice. Use T4, L4, A100, H100 or G4.", file=sys.stderr)
        return 2
    ensure_session(gpu)

    # Install ColabFold only once per persistent runtime. Marker is remote and survives runs.
    marker = "/content/af21_colabfold_ready.txt"
    # Check marker using a short remote kernel execution.
    probe_script = "from pathlib import Path\nprint('AF21_READY' if Path('/content/af21_colabfold_ready.txt').exists() else 'AF21_NOT_READY')\n"
    with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
        f.write(probe_script)
        probe_file = f.name
    try:
        probe_result = run_cmd(["exec", "-s", SESSION, "-f", probe_file], check=False, capture=True, timeout=45)
    finally:
        Path(probe_file).unlink(missing_ok=True)
    probe_output = (probe_result.stdout or "") + (probe_result.stderr or "")
    if "AF21_READY" not in probe_output:
        print("\nInstalling ColabFold into the remote runtime (first run only)...")
        install = run_cmd(["install", "-s", SESSION, "colabfold[alphafold-minus-jax]==1.6.3"], check=False)
        if install.returncode != 0:
            print("ColabFold installation failed. See the error above; the runtime has been left available for debugging.", file=sys.stderr)
            return install.returncode
        mark_script = "from pathlib import Path\nPath('/content/af21_colabfold_ready.txt').write_text('ready\\n')\nprint('ColabFold ready marker written')\n"
        with tempfile.NamedTemporaryFile("w", suffix=".py", delete=False, encoding="utf-8") as f:
            f.write(mark_script)
            marker_file = f.name
        try:
            marked = run_cmd(["exec", "-s", SESSION, "-f", marker_file], check=False, timeout=45)
        finally:
            Path(marker_file).unlink(missing_ok=True)
        if marked.returncode != 0:
            return marked.returncode

    now = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_base = re.sub(r"[^A-Za-z0-9_-]+", "_", output_dir.name).strip("_") or "prediction"
    job = f"{safe_base}_{now}"
    run_id = f"run_{now}_{os.getpid()}"
    remote_outdir = f"{REMOTE_ROOT}/{run_id}"
    remote_zip = f"{REMOTE_ROOT}/{run_id}.zip"
    config = {
        "sequences": sequences,
        "job_name": job,
        "remote_outdir": remote_outdir,
        "remote_cache": REMOTE_CACHE,
        "remote_zip": remote_zip,
        "model_type": "auto",
        "msa_mode": "mmseqs2_uniref_env",
        "pair_mode": "unpaired+paired",
        "num_recycles": args.recycles,
        "energy_minimize": args.relax,
        "use_templates": args.templates,
    }
    config_remote = f"/content/af21_config_{run_id}.json"
    with tempfile.TemporaryDirectory(prefix="af21_") as tmp:
        tmp = Path(tmp)
        config_local = tmp / "config.json"
        worker_local = tmp / "worker.py"
        config_local.write_text(json.dumps(config, indent=2), encoding="utf-8")
        worker_local.write_text(remote_worker_text(config_remote), encoding="utf-8")
        print("\nUploading run configuration...")
        up = run_cmd(["upload", "-s", SESSION, str(config_local), config_remote], check=False)
        if up.returncode != 0:
            return up.returncode
        print("\nRunning AlphaFold2 on the remote Colab runtime. This may take a while.")
        result = run_cmd(["exec", "-s", SESSION, "-f", str(worker_local)], check=False)
        if result.returncode != 0:
            print("\nRemote prediction failed. The Colab runtime has been kept alive; inspect it with 'af21 status' or open the Colab session URL.", file=sys.stderr)
            return result.returncode
        print("\nDownloading prediction archive...")
        archive_dir = output_dir / "archives"
        archive_dir.mkdir(parents=True, exist_ok=True)
        local_zip = archive_dir / "results_bundle.zip"
        down = run_cmd(["download", "-s", SESSION, remote_zip, str(local_zip)], check=False)
        if down.returncode != 0:
            print(f"Archive download failed. You can inspect the remote file with: colab ls -s {SESSION} {REMOTE_ROOT}", file=sys.stderr)
            return down.returncode
        try:
            with zipfile.ZipFile(local_zip) as zf:
                bad = zf.testzip()
                if bad:
                    raise zipfile.BadZipFile(f"Corrupt member: {bad}")
                # Guard against path traversal from a malformed archive.
                root = output_dir.resolve()
                for member in zf.infolist():
                    target = (output_dir / member.filename).resolve()
                    if target != root and root not in target.parents:
                        raise zipfile.BadZipFile(f"Unsafe archive path: {member.filename}")
                zf.extractall(output_dir)
        except Exception as exc:
            print(f"Could not extract results archive: {exc}", file=sys.stderr)
            return 1
    print("\nPrediction finished.")
    print(f"Local results: {output_dir}")
    print(f"Archive:       {output_dir / 'archives' / 'results_bundle.zip'}")
    print(f"Remote session remains available as '{SESSION}'. Use 'af21 stop' when finished.")
    return 0


def main():
    parser = argparse.ArgumentParser(prog="af21", description="Terminal AlphaFold2 via a persistent Google Colab runtime")
    sub = parser.add_subparsers(dest="command")
    runp = sub.add_parser("run", help="prompt for a sequence and run a prediction")
    runp.add_argument("--gpu", default="T4", help="GPU requested when creating a new runtime (default: T4)")
    runp.add_argument("--recycles", type=int, default=3, help="number of recycles (default: 3)")
    runp.add_argument("--relax", action="store_true", help="enable Amber relaxation (adds setup/compute cost)")
    runp.add_argument("--templates", action="store_true", help="enable template search (may require extra dependencies)")
    sub.add_parser("status", help="show the persistent Colab runtime status")
    sub.add_parser("stop", help="explicitly shut down the Colab runtime")
    sub.add_parser("url", help="print the Colab URL for the active runtime")
    sub.add_parser("help", help="show help")
    args = parser.parse_args()
    if args.command in (None, "run"):
        if args.command is None:
            args = argparse.Namespace(gpu="T4", recycles=3, relax=False, templates=False)
        return run_prediction(args)
    if not colab_available():
        return 2
    if args.command == "status":
        result = run_cmd(["status", "-s", SESSION], check=False)
        if result.returncode:
            print("No active runtime found, or authentication is required.")
        return result.returncode
    if args.command == "stop":
        result = run_cmd(["stop", "-s", SESSION], check=False)
        if result.returncode == 0:
            print("Colab runtime stopped. Any files only on the remote VM may be lost; downloaded local results are safe.")
        return result.returncode
    if args.command == "url":
        return run_cmd(["url", "-s", SESSION], check=False).returncode
    parser.print_help()
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
