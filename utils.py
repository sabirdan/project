import os
import csv
import io
import numpy as np
from datetime import datetime

import cv2
from PyQt5.QtCore import Qt
from PyQt5.QtGui import (
    QImage, QPixmap, QPainter, QPen, QGuiApplication
)
from PyQt5.QtWidgets import QLabel

FACE_REC_OK = False
face_recognition = None

try:
    import face_recognition
    try:
        import face_recognition_models
        FACE_REC_OK = True
    except Exception as e:
        FACE_REC_OK = False
except ImportError as e:
    FACE_REC_OK = False
except Exception as e:
    FACE_REC_OK = False


def _safe_csv_cell(s: str) -> str:
    s = (s or "").strip()
    if s and s[0] in ("=", "+", "-", "@"):
        return "'" + s
    return s

def _now_date_str():
    return datetime.now().strftime("%d-%m-%Y")


def _now_time_str():
    return datetime.now().strftime("%H:%M:%S")


def _ensure_dirs(base_dir: str):
    ops_dir = os.path.join(base_dir, "operators")
    os.makedirs(ops_dir, exist_ok=True)
    return ops_dir


def _csv_path(base_dir: str):
    return os.path.join(base_dir, "operators_db.csv")


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
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing, True)

    p.setPen(Qt.NoPen)
    p.setBrush(Qt.green if ok else Qt.red)
    p.drawEllipse(0, 0, size - 1, size - 1)

    pen2 = QPen(Qt.white)
    pen2.setWidth(3)
    p.setPen(pen2)
    if ok:
        p.drawLine(int(size * 0.25), int(size * 0.55), int(size * 0.45), int(size * 0.75))
        p.drawLine(int(size * 0.43), int(size * 0.73), int(size * 0.78), int(size * 0.30))
    else:
        p.drawLine(int(size * 0.30), int(size * 0.30), int(size * 0.70), int(size * 0.70))
        p.drawLine(int(size * 0.70), int(size * 0.30), int(size * 0.30), int(size * 0.70))

    p.end()
    return pm


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
            except Exception:
                continue
            if rid == op_id:
                return row
    return None


def _iter_operator_photos(ops_dir: str):
    if not os.path.isdir(ops_dir):
        return
    for name in os.listdir(ops_dir):
        if not name.lower().endswith(".jpg"):
            continue
        if not name.startswith("ID_"):
            continue
        path = os.path.join(ops_dir, name)
        yield name, path


FR_TOLERANCE = 0.45


def _fr_prepare_rgb_from_bgr(frame_bgr):
    if frame_bgr is None:
        return None

    if not isinstance(frame_bgr, np.ndarray):
        try:
            frame_bgr = np.asarray(frame_bgr)
        except Exception:
            return None

    if frame_bgr.dtype != np.uint8:
        try:
            frame_bgr = np.clip(frame_bgr, 0, 255).astype(np.uint8, copy=False)
        except Exception:
            frame_bgr = frame_bgr.astype(np.uint8, copy=True)

    if frame_bgr.ndim == 2:
        frame_bgr = cv2.cvtColor(frame_bgr, cv2.COLOR_GRAY2BGR)
    elif frame_bgr.ndim == 3 and frame_bgr.shape[2] == 4:
        frame_bgr = cv2.cvtColor(frame_bgr, cv2.COLOR_BGRA2BGR)
    elif frame_bgr.ndim != 3 or frame_bgr.shape[2] != 3:
        return None

    rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    rgb = np.ascontiguousarray(rgb, dtype=np.uint8)

    if not rgb.flags["C_CONTIGUOUS"]:
        rgb = rgb.copy(order="C")

    return rgb


def fr_extract_single_face_encoding_from_bgr(frame_bgr, model="hog"):
    if not FACE_REC_OK:
        return None, None
    if frame_bgr is None:
        return None, None

    try:
        rgb = _fr_prepare_rgb_from_bgr(frame_bgr)
        if rgb is not None:
            locs = face_recognition.face_locations(rgb, model=model)
            if len(locs) == 1:
                encs = face_recognition.face_encodings(rgb, locs)
                if len(encs) == 1:
                    return encs[0], locs[0]
    except RuntimeError:
        pass
    except Exception:
        pass

    try:
        bgr = frame_bgr
        if not isinstance(bgr, np.ndarray):
            bgr = np.asarray(bgr)

        if bgr.dtype != np.uint8:
            bgr = np.clip(bgr, 0, 255).astype(np.uint8)

        if bgr.ndim == 2:
            bgr = cv2.cvtColor(bgr, cv2.COLOR_GRAY2BGR)
        elif bgr.ndim == 3 and bgr.shape[2] == 4:
            bgr = cv2.cvtColor(bgr, cv2.COLOR_BGRA2BGR)
        elif bgr.ndim != 3 or bgr.shape[2] != 3:
            return None, None

        ok, buf = cv2.imencode(".jpg", bgr, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not ok:
            return None, None

        bio = io.BytesIO(buf.tobytes())
        img = face_recognition.load_image_file(bio)

        locs = face_recognition.face_locations(img, model=model)
        if len(locs) != 1:
            return None, None

        encs = face_recognition.face_encodings(img, locs)
        if len(encs) != 1:
            return None, None

        return encs[0], locs[0]
    except Exception:
        return None, None


def fr_extract_single_face_encoding_from_file(path: str, model="hog"):
    if not FACE_REC_OK or not path or not os.path.exists(path):
        return None

    try:
        img = face_recognition.load_image_file(path)
        locs = face_recognition.face_locations(img, model=model)
        if len(locs) != 1:
            return None
        encs = face_recognition.face_encodings(img, locs)
        if len(encs) != 1:
            return None
        return encs[0]
    except Exception:
        return None


def fr_find_match_id(known_list, probe_enc, tolerance=FR_TOLERANCE):
    if not FACE_REC_OK or probe_enc is None or not known_list:
        return None

    ids = [kid for kid, _ in known_list]
    encs = [kenc for _, kenc in known_list]

    try:
        matches = face_recognition.compare_faces(encs, probe_enc, tolerance=tolerance)
        if True in matches:
            return ids[matches.index(True)]
        return None
    except Exception:
        return None


def fr_compare_two(ref_enc, live_enc, tolerance=FR_TOLERANCE) -> bool:
    if not FACE_REC_OK or ref_enc is None or live_enc is None:
        return False
    try:
        return bool(face_recognition.compare_faces([ref_enc], live_enc, tolerance=tolerance)[0])
    except Exception:
        return False


def fr_load_known_encodings(ops_dir: str, exclude_id: int = None):
    if not FACE_REC_OK:
        return []

    result = []
    for name, path in _iter_operator_photos(ops_dir):
        try:
            raw_id = name.replace("ID_", "").replace(".jpg", "")
            pid = int(raw_id)
        except Exception:
            continue

        if exclude_id is not None and pid == exclude_id:
            continue

        enc = fr_extract_single_face_encoding_from_file(path)
        if enc is not None:
            result.append((pid, enc))

    return result


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
        print(f"Пустой кадр или путь: {filepath}")
        return False

    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
    except Exception as e:
        print(f"Ошибка создания директории: {e}")
        return False

    save_frame = frame_bgr

    if face_loc:
        try:
            top, right, bottom, left = face_loc
            h, w = frame_bgr.shape[:2]
            top = max(0, min(top, h - 1))
            left = max(0, min(left, w - 1))
            bottom = max(top + 1, min(bottom, h))
            right = max(left + 1, min(right, w))

            if bottom > top and right > left:
                face_crop = frame_bgr[top:bottom, left:right]
                if face_crop is not None and face_crop.size > 0:
                    if face_crop.dtype != np.uint8:
                        face_crop = face_crop.astype(np.uint8)
                    if face_crop.max() > 255 or face_crop.min() < 0:
                        face_crop = np.clip(face_crop, 0, 255).astype(np.uint8)
                    save_frame = face_crop
                else:
                    save_frame = frame_bgr
            else:
                save_frame = frame_bgr

        except Exception as e:
            print(f"Ошибка при обрезке лица: {e}")
            save_frame = frame_bgr

    try:
        success = cv2.imwrite(filepath, save_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
        if not success:
            encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 95]
            result, encimg = cv2.imencode('.jpg', save_frame, encode_param)
            if result:
                with open(filepath, 'wb') as f:
                    f.write(encimg.tobytes())
                success = True

        if success:
            return True
        else:
            return False

    except Exception as e:
        print(f"Ошибка при сохранении файла {filepath}: {e}")
        return False