import os
import csv
import io
import numpy as np
from datetime import datetime

import cv2
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QImage, QPixmap, QGuiApplication
)
from PyQt5.QtWidgets import QLabel

# CSV_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CSV_DIRECTORY = r"C:\Users\user\Desktop"

CASCADE_PATH = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
FACE_CASCADE = cv2.CascadeClassifier(CASCADE_PATH)

OPENCV_FACE_OK = False
try:
    RECOGNIZER = cv2.face.LBPHFaceRecognizer_create()
    OPENCV_FACE_OK = True
except AttributeError:
    RECOGNIZER = None
    print("Внимание: LBPHFaceRecognizer недоступен. Установите opencv-contrib-python.")


def _safe_csv_cell(s: str) -> str:
    s = (s or "").strip()
    if s and s[0] in ("=", "+", "-", "@"):
        return "'" + s
    return s

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
    if os.path.exists(csv_file):
        return
    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow([
            "id", "last_name", "first_name", "middle_name", "age",
            "date", "time", "software_start_time", "drive_duration"
        ])

def _next_id(csv_file: str) -> int:
    max_id = 0
    if not os.path.exists(csv_file):
        return 1
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                max_id = max(max_id, int(str(row.get("id", "0")).strip() or "0"))
            except Exception:
                pass
    return max_id + 1

def _id_str(n: int) -> str:
    return str(n).zfill(5)

def _make_icon(ok: bool, size: int = 28) -> QPixmap:
    base_dir = os.path.dirname(os.path.abspath(__file__))
    img_name = "accept.png" if ok else "cancel.png"
    img_path = os.path.join(base_dir, "assets", img_name)
    pm = QPixmap(img_path)
    if not pm.isNull():
        return pm.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return QPixmap()

def _parse_hms_to_seconds(s: str) -> int:
    try:
        parts = (s or "00:00:00").strip().split(":")
        if len(parts) != 3:
            return 0
        h, m, sec = [int(x) for x in parts]
        return h * 3600 + m * 60 + sec
    except Exception:
        return 0

def _seconds_to_hms(x: int) -> str:
    x = max(0, int(x))
    h = x // 3600
    x %= 3600
    m = x // 60
    s = x % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

def _find_operator_by_id(csv_file: str, op_id: int):
    if not os.path.exists(csv_file):
        return None
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                rid = int(str(row.get("id", "")).strip() or "0")
                if rid == op_id:
                    return row
            except Exception:
                continue
    return None


def get_cv_face(frame_bgr):
    if frame_bgr is None:
        return None, None
    
    gray = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, 1.1, 5, minSize=(100, 100))
    
    if len(faces) == 1:
        (x, y, w, h) = faces[0]
        face_gray = gray[y:y+h, x:x+w]
        return face_gray, (y, x+w, y+h, x)
    return None, None

def cv_compare_faces(ref_gray, live_gray, threshold=65):
    if not OPENCV_FACE_OK or ref_gray is None or live_gray is None:
        return False
    try:
        RECOGNIZER.train([ref_gray], np.array([1]))
        _, confidence = RECOGNIZER.predict(live_gray)
        return confidence < threshold
    except Exception:
        return False

def cv_load_known_faces(ops_dir, exclude_id=None):
    known = []
    if not os.path.isdir(ops_dir):
        return known
    
    for name in os.listdir(ops_dir):
        if not (name.startswith("ID_") and name.lower().endswith(".jpg")):
            continue
        try:
            raw_id = name.replace("ID_", "").replace(".jpg", "")
            pid = int(raw_id)
            if exclude_id is not None and pid == exclude_id:
                continue
            
            img = _opencv_imread_unicode(os.path.join(ops_dir, name))
            face_gray, _ = get_cv_face(img)
            if face_gray is not None:
                known.append((pid, face_gray))
        except Exception:
            continue
    return known

def cv_find_match(known_faces, live_gray):
    for pid, ref_gray in known_faces:
        if cv_compare_faces(ref_gray, live_gray):
            return pid
    return None


def _crop_to_aspect(img, target_w, target_h):
    h, w = img.shape[:2]
    aspect_img = w / h
    aspect_target = target_w / target_h

    if aspect_img > aspect_target:
        new_w = int(h * aspect_target)
        offset = (w - new_w) // 2
        return img[:, offset:offset + new_w]
    else:
        new_h = int(w / aspect_target)
        offset = (h - new_h) // 2
        return img[offset:offset + new_h, :]

def _draw_to_label_with_dpr(frame_bgr, label: QLabel):
    screen = label.screen() or QGuiApplication.primaryScreen()
    dpr = float(screen.devicePixelRatio()) if screen else 1.0

    view_w = label.width()
    view_h = label.height()

    target_w = max(1, int(view_w * dpr))
    target_h = max(1, int(view_h * dpr))

    cropped = _crop_to_aspect(frame_bgr, target_w, target_h)
    resized = cv2.resize(cropped, (target_w, target_h), interpolation=cv2.INTER_AREA)

    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    h, w, ch = rgb.shape
    qimg = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)

    pm = QPixmap.fromImage(qimg)
    pm.setDevicePixelRatio(dpr)
    label.setPixmap(pm)

def _opencv_save_jpg(frame_bgr, filepath: str, face_loc=None):
    if frame_bgr is None or not filepath:
        return False
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        save_frame = frame_bgr
        if face_loc:
            top, right, bottom, left = face_loc
            save_frame = frame_bgr[top:bottom, left:right]

        if save_frame.size == 0:
            return False

        success, buffer = cv2.imencode(".jpg", save_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if success:
            with open(filepath, "wb") as f:
                f.write(buffer)
            return True
        return False
    except Exception:
        return False
    
def _opencv_imread_unicode(filepath):
    try:
        import numpy as np
        img_array = np.fromfile(filepath, dtype=np.uint8)
        return cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    except Exception as e:
        print(f"Ошибка при чтении файла {filepath}: {e}")
        return None