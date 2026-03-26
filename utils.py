import os
import csv
import numpy as np
from datetime import datetime
import cv2
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QImage, QPixmap, QGuiApplication
from PyQt5.QtWidgets import QLabel

CSV_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
FACE_CASCADE = cv2.CascadeClassifier(CASCADE_PATH)

def _safe_csv_cell(s: str) -> str:
    s = (s or "").strip()
    return f"'{s}" if s and s[0] in ("=", "+", "-", "@") else s

def _now_date_str():
    return datetime.now().strftime("%d.%m.%Y")

def _now_time_str():
    return datetime.now().strftime("%H:%M:%S")

def _ensure_dirs(base_dir: str):
    ops_dir = os.path.join(CSV_DIRECTORY, "operators")
    os.makedirs(ops_dir, exist_ok=True)
    return ops_dir

def _csv_path(base_dir: str = None):
    return os.path.join(CSV_DIRECTORY, "operators_db.csv")

def _ensure_csv(csv_file: str):
    if not os.path.exists(csv_file):
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(["id", "last_name", "first_name", "middle_name", "age", "date", "time", "software_start_time", "drive_duration"])

def _next_id(csv_file: str) -> int:
    if not os.path.exists(csv_file): return 1
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        return max([0] + [int(str(row.get("id", "0")).strip() or "0") for row in csv.DictReader(f) if row.get("id")]) + 1

def _id_str(n: int) -> str:
    return str(n).zfill(5)

def _make_icon(ok: bool, size: int = 28) -> QPixmap:
    return QPixmap(f"assets/{'accept.png' if ok else 'cancel.png'}").scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

def _parse_hms_to_seconds(s: str) -> int:
    parts = (s or "00:00:00").strip().split(":")
    return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2]) if len(parts) == 3 else 0

def _seconds_to_hms(x: int) -> str:
    x = max(0, int(x))
    return f"{x // 3600:02d}:{(x % 3600) // 60:02d}:{x % 60:02d}"

def _find_operator_by_id(csv_file: str, op_id: int):
    if not os.path.exists(csv_file): return None
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if int(str(row.get("id", "")).strip() or "0") == op_id:
                return row
    return None

def get_cv_face(frame_bgr):
    if frame_bgr is None: return None, None
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
    if len(faces) == 1:
        x, y, w, h = faces[0]
        return gray[y:y+h, x:x+w], (y, x+w, y+h, x)
    return None, None

def cv_compare_faces(ref_gray, live_gray, threshold=0.55):
    if ref_gray is None or live_gray is None: return False
    ref_eq = cv2.equalizeHist(cv2.resize(ref_gray, (150, 150)))
    live_eq = cv2.equalizeHist(cv2.resize(live_gray, (150, 150)))
    return float(cv2.matchTemplate(ref_eq, live_eq, cv2.TM_CCOEFF_NORMED)[0][0]) >= threshold

def cv_load_known_faces(ops_dir, exclude_id=None):
    known = []
    if not os.path.isdir(ops_dir): return known
    for name in os.listdir(ops_dir):
        if name.startswith("ID_") and name.lower().endswith(".jpg"):
            pid = int(name.replace("ID_", "").replace(".jpg", ""))
            if exclude_id is None or pid != exclude_id:
                face_gray, _ = get_cv_face(_opencv_imread_unicode(os.path.join(ops_dir, name)))
                if face_gray is not None: known.append((pid, face_gray))
    return known

def cv_find_match(known_faces, live_gray):
    for pid, ref_gray in known_faces:
        if cv_compare_faces(ref_gray, live_gray): return pid
    return None

def _crop_to_aspect(img, target_w, target_h):
    h, w = img.shape[:2]
    aspect_img, aspect_target = w / h, target_w / target_h
    if aspect_img > aspect_target:
        new_w = int(h * aspect_target)
        offset = (w - new_w) // 2
        return img[:, offset:offset + new_w]
    new_h = int(w / aspect_target)
    offset = (h - new_h) // 2
    return img[offset:offset + new_h, :]

def _draw_to_label_with_dpr(frame_bgr, label: QLabel):
    screen = label.screen() or QGuiApplication.primaryScreen()
    dpr = float(screen.devicePixelRatio()) if screen else 1.0
    target_w, target_h = max(1, int(label.width() * dpr)), max(1, int(label.height() * dpr))
    rgb = cv2.cvtColor(cv2.resize(_crop_to_aspect(frame_bgr, target_w, target_h), (target_w, target_h), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    pm = QPixmap.fromImage(QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888))
    pm.setDevicePixelRatio(dpr)
    label.setPixmap(pm)

def _opencv_save_jpg(frame_bgr, filepath: str, face_loc=None):
    if frame_bgr is None or not filepath: return False
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    save_frame = frame_bgr[face_loc[0]:face_loc[2], face_loc[3]:face_loc[1]] if face_loc else frame_bgr
    if save_frame.size == 0: return False
    success, buffer = cv2.imencode(".jpg", save_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if success:
        with open(filepath, "wb") as f: f.write(buffer)
        return True
    return False

def _opencv_imread_unicode(filepath):
    return cv2.imdecode(np.fromfile(filepath, dtype=np.uint8), cv2.IMREAD_COLOR)