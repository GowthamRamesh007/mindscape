#!/usr/bin/env python3
"""Supabase backup utility

Generates CSV dumps of selected tables and optionally downloads all files from
the configured storage bucket. The script can be scheduled (cron) or triggered
manually before a production release.

Usage:
    python backup_supabase.py [--tables table1,table2] [--download-storage]

All dumps are placed under `data/backups/<YYYYMMDD>/`.
"""

import os
import csv
import sys
import argparse
from datetime import datetime
from pathlib import Path

# Import supabase helpers from the project
sys.path.append(str(Path(__file__).resolve().parents[2]))  # add project root to PYTHONPATH
from backend.services.supabase_service import get_supabase_admin, get_supabase_anon, is_valid_supabase_config, CONFIG_FILE

DEFAULT_TABLES = [
    "submissions",
    "teams",
    "profiles",
    "competition",
    "deadline",
]

def dump_table_to_csv(client, table_name: str, output_path: Path):
    """Fetch all rows from `table_name` and write them as CSV.

    The Supabase client returns a dictionary with a ``data`` key containing a
    list of rows.  Column order is derived from the keys of the first row.
    """
    try:
        res = client.table(table_name).select("*").execute()
        rows = res.data or []
        if not rows:
            print(f"[Backup] Table '{table_name}' is empty – creating empty CSV.")
        else:
            print(f"[Backup] Exporting {len(rows)} rows from '{table_name}'.")
        # Determine column order
        fieldnames = rows[0].keys() if rows else []
        with open(output_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            for row in rows:
                writer.writerow(row)
    except Exception as e:
        print(f"[Backup][Error] Failed to dump table '{table_name}': {e}")

def download_storage_bucket(client, bucket_name: str, dest_dir: Path):
    """Download every file from `bucket_name` to `dest_dir` preserving paths.

    Supabase Storage does not provide a recursive download API, so we list all
    objects and fetch each one individually.
    """
    try:
        storage = client.storage.from_(bucket_name)
        files = storage.list(path="").get("data", [])
        if not files:
            print(f"[Backup] Storage bucket '{bucket_name}' is empty.")
            return
        print(f"[Backup] Downloading {len(files)} objects from bucket '{bucket_name}'.")
        for obj in files:
            name = obj.get("name")
            if not name:
                continue
            file_path = dest_dir / name
            file_path.parent.mkdir(parents=True, exist_ok=True)
            data = storage.download(name).get("data")
            if data is None:
                print(f"[Backup][Warn] Could not download '{name}'.")
                continue
            with open(file_path, "wb") as f:
                f.write(data)
    except Exception as e:
        print(f"[Backup][Error] Storage download failed: {e}")

def main():
    parser = argparse.ArgumentParser(description="Supabase backup utility")
    parser.add_argument(
        "--tables",
        type=str,
        help="Comma‑separated list of tables to dump (default: built‑in list)",
    )
    parser.add_argument(
        "--download-storage",
        action="store_true",
        help="Download all files from the configured storage bucket",
    )
    args = parser.parse_args()

    if not is_valid_supabase_config():
        print("[Backup][Error] Supabase configuration is missing or invalid.")
        sys.exit(1)

    client = get_supabase_admin() or get_supabase_anon()
    if client is None:
        print("[Backup][Error] Unable to initialise a Supabase client.")
        sys.exit(1)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_root = Path(__file__).resolve().parents[2] / "data" / "backups" / timestamp
    backup_root.mkdir(parents=True, exist_ok=True)

    tables = args.tables.split(",") if args.tables else DEFAULT_TABLES
    for table in tables:
        table = table.strip()
        if not table:
            continue
        csv_path = backup_root / f"{table}.csv"
        dump_table_to_csv(client, table, csv_path)

    if args.download_storage:
        bucket_name = "mindscape-reels"
        if CONFIG_FILE.is_file():
            try:
                import json
                data = json.loads(CONFIG_FILE.read_text())
                bucket_name = data.get("storage_bucket", bucket_name)
            except Exception:
                pass
        storage_dir = backup_root / "storage"
        storage_dir.mkdir(parents=True, exist_ok=True)
        download_storage_bucket(client, bucket_name, storage_dir)

    print(f"[Backup] Completed. Files stored in {backup_root}")

if __name__ == "__main__":
    main()
