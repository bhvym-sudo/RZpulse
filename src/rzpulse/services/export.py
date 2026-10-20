import csv
import json
import os
from pathlib import Path

from rzpulse.utils.security import redact


def export_records(path: Path, records: list[dict], secrets: tuple[str, ...] = ()) -> None:
    """Exclusive create, owner-only permissions, masked values, spreadsheet-safe CSV."""
    if path.suffix.lower() not in {".json", ".csv"}:
        raise ValueError("Use a .json or .csv filename.")
    data = redact(records, secrets)
    with open(path, "x", encoding="utf-8", newline="", opener=lambda p, f: os.open(p, f, 0o600)) as f:
        if path.suffix.lower() == ".json":
            json.dump(data, f, indent=2, ensure_ascii=False)
        elif path.suffix.lower() == ".csv":
            fields = sorted({key for row in data for key in row})
            writer = csv.writer(f)
            def safe_cell(value):
                text = json.dumps(value) if isinstance(value, (list, dict)) else str(value)
                return "'" + text if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")) else text
            writer.writerow([safe_cell(field) for field in fields])
            for row in data:
                writer.writerow([safe_cell(row.get(field, "")) for field in fields])
        else:
            raise ValueError("Use a .json or .csv filename.")
