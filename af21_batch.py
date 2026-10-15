#!/usr/bin/env python3
"""
Run multiple AlphaFold21 predictions sequentially using the existing `af21` CLI.

Input CSV/TSV must contain an ID column and a sequence column, e.g.:
ID,Sequence
ID_01,QTKLARLHYKYKRRHSIWRKRKEKYDNKNDYGRKIGKKWQVWK
"""
from __future__ import annotations

import argparse
import csv
import re
import shutil
import subprocess
import sys
from pathlib import Path


def safe_folder_name(value: str) -> str:
    # Preserve readable IDs while preventing path traversal.
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    if not cleaned:
        raise ValueError(f"Invalid/empty ID: {value!r}")
    return cleaned.lower()


def load_rows(path: Path, id_column: str, sequence_column: str):
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        sample = handle.read(4096)
        handle.seek(0)
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(handle, dialect=dialect)
        if not reader.fieldnames:
            raise ValueError("Input file has no header row.")
        headers = [h.strip() for h in reader.fieldnames if h]
        if id_column not in headers or sequence_column not in headers:
            raise ValueError(
                f"Required columns not found. Found: {headers}. "
                f"Expected columns named {id_column!r} and {sequence_column!r}. "
                "Use --id-column and --sequence-column to specify other names."
            )
        rows = []
        seen = set()
        for line_number, row in enumerate(reader, start=2):
            identifier = (row.get(id_column) or "").strip()
            sequence = re.sub(r"\s+", "", (row.get(sequence_column) or "")).upper()
            if not identifier and not sequence:
                continue
            if not identifier:
                raise ValueError(f"Missing ID on input line {line_number}.")
            if not sequence:
                raise ValueError(f"Missing sequence for {identifier!r} on line {line_number}.")
            folder = safe_folder_name(identifier)
            if folder in seen:
                raise ValueError(
                    f"IDs produce duplicate output folder {folder!r}; IDs must be unique."
                )
            seen.add(folder)
            rows.append((identifier, sequence, folder))
    if not rows:
        raise ValueError("No prediction rows found.")
    return rows


def main():
    parser = argparse.ArgumentParser(
        description="Run sequential AlphaFold21 predictions from a CSV/TSV table."
    )
    parser.add_argument("input_file", help="CSV/TSV file containing IDs and sequences")
    parser.add_argument("--id-column", default="ID", help="ID column name (default: ID)")
    parser.add_argument(
        "--sequence-column", default="Sequence",
        help="protein sequence column name (default: Sequence)"
    )
    parser.add_argument(
        "--output-root", default=".",
        help="parent directory for per-ID results (default: current directory)"
    )
    parser.add_argument(
        "--af21-command", default="af21",
        help="existing af21 launcher command (default: af21)"
    )
    parser.add_argument(
        "--continue-on-error", action="store_true",
        help="continue with later rows if one prediction fails"
    )
    args = parser.parse_args()

    input_path = Path(args.input_file).expanduser().resolve()
    if not input_path.is_file():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 2

    try:
        rows = load_rows(input_path, args.id_column, args.sequence_column)
    except Exception as exc:
        print(f"ERROR reading input: {exc}", file=sys.stderr)
        return 2

    launcher = shutil.which(args.af21_command)
    if not launcher:
        print(f"ERROR: could not find launcher {args.af21_command!r} on PATH.", file=sys.stderr)
        print("Activate the af21 Conda environment and check `which af21`.", file=sys.stderr)
        return 2

    output_root = Path(args.output_root).expanduser().resolve()
    output_root.mkdir(parents=True, exist_ok=True)

    print(f"Input file: {input_path}")
    print(f"Predictions queued: {len(rows)}")
    print(f"Output root: {output_root}")
    print("Runs are sequential; repeated sequences with different IDs are predicted separately.")
    print("The existing Colab runtime will be reused by the af21 launcher.\n")

    failures = []
    for index, (identifier, sequence, folder) in enumerate(rows, start=1):
        target = output_root / folder
        best_model = target / "structures" / "best_model.pdb"

        # A non-empty best_model.pdb marks a completed prediction.
        # Preserve and skip completed results; retry incomplete folders safely.
        if best_model.is_file() and best_model.stat().st_size > 0:
            print(f"[{index}/{len(rows)}] SKIP {identifier}: completed result exists: {best_model}")
            continue

        resume_existing = target.exists() and any(target.iterdir())
        target.mkdir(parents=True, exist_ok=True)
        if resume_existing:
            print(
                f"[{index}/{len(rows)}] RETRY {identifier}: best_model.pdb is missing; "
                f"existing files will be preserved in {target}",
                flush=True,
            )

        print("\n" + "=" * 78)
        print(f"[{index}/{len(rows)}] {identifier} | {len(sequence)} residues/chars | {target}")
        print("=" * 78, flush=True)

        # Current af21 interactive interface asks for sequence first, then output directory.
        payload = f"{sequence}\n{target}\n" + ("y\n" if resume_existing else "")
        try:
            result = subprocess.run(
                [launcher],
                input=payload,
                text=True,
                check=False,
            )
        except KeyboardInterrupt:
            print("\nInterrupted by user. The current remote session was not explicitly stopped.")
            return 130
        except Exception as exc:
            failures.append((identifier, str(exc)))
            print(f"ERROR launching {identifier}: {exc}", file=sys.stderr)
            if not args.continue_on_error:
                break
            continue

        if result.returncode != 0:
            failures.append((identifier, f"af21 exited with code {result.returncode}"))
            print(f"FAILED: {identifier}", file=sys.stderr)
            if not args.continue_on_error:
                break
        else:
            print(f"COMPLETED: {identifier} -> {target}", flush=True)

    print("\n" + "=" * 78)
    print("BATCH SUMMARY")
    print(f"Total rows: {len(rows)}")
    print(f"Failures/skipped: {len(failures)}")
    for identifier, reason in failures:
        print(f" - {identifier}: {reason}")
    print(f"Results root: {output_root}")
    print("The Colab runtime remains available; shut it down separately with `af21 stop` when finished.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
