"""Backward-compatible launcher: `python ingest.py --source chub`."""

from ingestion.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
