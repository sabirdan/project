import os

CSV_DIRECTORY = r"C:\Users\user\Desktop\Профессионалы регион 2026\project-championat"

def _ensure_dirs(base_dir: str):
    ops_dir = os.path.join(CSV_DIRECTORY, "operators")
    os.makedirs(ops_dir, exist_ok=True)
    return ops_dir

def _csv_path(base_dir: str = None):
    return os.path.join(CSV_DIRECTORY, "operators_db.csv")

def _id_str(n: int) -> str:
    return str(n).zfill(5)

def _parse_hms_to_seconds(s: str) -> int:
    parts = (s or "00:00:00").strip().split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0