import os
import csv
import numpy as np
from datetime import datetime
import cv2
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QImage, QPixmap, QGuiApplication, QPainter, QBrush, QColor, QPolygon, QFont
from PyQt5.QtWidgets import QLabel, QLineEdit, QWidget, QVBoxLayout, QHBoxLayout, QPushButton

COLOR_BG = "#D9D9D9"
COLOR_BTN_BG = "#2C2C2C"
COLOR_GREEN = "#44CC29"
COLOR_DISABLED = "#C7C7C7"

CSV_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
FACE_CASCADE = cv2.CascadeClassifier(CASCADE_PATH)

# РАБОТА С CSV И СИСТЕМНЫМИ ДАННЫМИ

def csv_path(base_dir: str = None):
    return os.path.join(CSV_DIRECTORY, "operators_db.csv")

def ensure_csv(csv_file: str):
    if not os.path.exists(csv_file):
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            headers = [
                "id", "last_name", "first_name", "middle_name", 
                "age", "date", "time", "software_start_time", "drive_duration"
            ]
            csv.writer(f).writerow(headers)

def next_id(csv_file: str) -> int:
    if not os.path.exists(csv_file):
        return 1
    
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        ids = []
        for row in reader:
            if row.get("id"):
                val = str(row.get("id", "0")).strip()
                if not val:
                    val = "0"
                ids.append(int(val))
                
        if not ids:
            return 1
        return max(ids) + 1

def id_str(n: int) -> str:
    return str(n).zfill(5)

def find_operator_by_id(csv_file: str, op_id: int):
    if not os.path.exists(csv_file):
        return None
        
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            val = str(row.get("id", "")).strip()
            if not val:
                val = "0"
            if int(val) == op_id:
                return row
    return None

def update_db(csv_file: str, op_id, data_to_update: dict):
    if not os.path.exists(csv_file):
        return

    target_id = str(op_id).strip()
    rows = []
    fieldnames = []

    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if reader.fieldnames:
            fieldnames = list(reader.fieldnames)
        rows = list(reader)

    for key in data_to_update.keys():
        if key not in fieldnames:
            fieldnames.append(key)

    for row in rows:
        val = str(row.get("id", "")).strip()
        if not val:
            val = "0"
        if val == target_id:
            row.update(data_to_update)
            break

    with open(csv_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

# РАБОТА СО ВРЕМЕНЕМ

def now_date_str():
    return datetime.now().strftime("%d.%m.%Y")

def now_time_str():
    return datetime.now().strftime("%H:%M:%S")

def parse_hms_to_seconds(s: str) -> int:
    parts = (s or "00:00:00").strip().split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0

def seconds_to_hms(x: int) -> str:
    x = max(0, int(x))
    h = x // 3600
    m = (x % 3600) // 60
    s = x % 60
    return f"{h:02d}:{m:02d}:{s:02d}"

# КОМПЬЮТЕРНОЕ ЗРЕНИЕ (OPENCV) И ПОИСК ЛИЦ

def process_face(frame, draw=False, color=(0, 255, 0)):
    if frame is None:
        return None, None
        
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray, 1.3, 5, minSize=(100, 100))
    
    if len(faces) > 0:
        x, y, w, h = max(faces, key=lambda f: f[2]*f[3])
        
        if draw:
            cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
            
        return gray[y:y+h, x:x+w], (x, y, w, h)
        
    return None, None

def cv_compare_faces(ref_gray, live_gray, threshold=0.35):
    if ref_gray is None or live_gray is None:
        return False
        
    ref_eq = cv2.equalizeHist(cv2.resize(ref_gray, (150, 150)))
    live_eq = cv2.equalizeHist(cv2.resize(live_gray, (150, 150)))
    
    match = cv2.matchTemplate(ref_eq, live_eq, cv2.TM_CCOEFF_NORMED)
    return float(match[0][0]) >= threshold

def cv_load_known_faces(ops_dir, exclude_id=None):
    known = []
    if not os.path.isdir(ops_dir):
        return known
        
    for name in os.listdir(ops_dir):
        is_id = name.startswith("ID_")
        is_jpg = name.lower().endswith(".jpg")
        
        if is_id and is_jpg:
            pid_str = name.replace("ID_", "").replace(".jpg", "")
            pid = int(pid_str)
            
            if exclude_id is None or pid != exclude_id:
                path = os.path.join(ops_dir, name)
                img = opencv_imread_unicode(path)
                
                if img is not None:
                    face_gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
                    known.append((pid, face_gray))
    return known

def cv_find_match(known_faces, live_gray):
    for pid, ref_gray in known_faces:
        if cv_compare_faces(ref_gray, live_gray):
            return pid
    return None

# РАБОТА С ИНТЕРФЕЙСОМ (PYQT5) И ОТРИСОВКА

class BaseWindow(QWidget):
    def __init__(self, width, height, title):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(width, height)
        self.setWindowTitle(title)
        self.setStyleSheet(f"background-color: {COLOR_BG};")

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)

        top_grey = QWidget(self)
        top_grey.setFixedHeight(30)
        top_layout = QHBoxLayout(top_grey)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("X", top_grey)
        self.btn_close.setFixedSize(45, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            f"color: red; background: transparent; border: none; font-size: 24px; font-weight: bold;"
        )
        self.btn_close.clicked.connect(self.close)
        
        top_layout.addWidget(self.btn_close)
        self.main_layout.addWidget(top_grey)

        top_white = QWidget(self)
        top_white.setFixedHeight(4)
        top_white.setStyleSheet("background-color: white;")
        self.main_layout.addWidget(top_white)

        self.content_container = QWidget(self)
        self.main_layout.addWidget(self.content_container)

class ShapeWidget(QWidget):
    def __init__(self, shape_type, color, size=40, parent=None):
        super().__init__(parent)
        self.shape_type = shape_type
        self.color = color
        self.setFixedSize(size, size)

    def set_color(self, new_color):
        self.color = new_color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(self.color)))
        
        if self.shape_type == "circle":
            painter.drawEllipse(0, 0, self.width(), self.height())
        elif self.shape_type == "triangle":
            points = [
                QPoint(self.width() // 2, 0),
                QPoint(0, self.height()),
                QPoint(self.width(), self.height())
            ]
            painter.drawPolygon(QPolygon(points))
        elif self.shape_type == "square":
            painter.drawRect(0, 0, self.width(), self.height())

def create_label(text, font_size=14, bold=False, color=None, align=None):
    lbl = QLabel(text)
    font = QFont("Times New Roman", font_size)
    if bold:
        font.setBold(True)
    lbl.setFont(font)
    if color:
        lbl.setStyleSheet(f"color: {color};")
    if align:
        lbl.setAlignment(align)
    return lbl

def make_icon(ok: bool, size: int = 28) -> QPixmap:
    name = 'accept.png' if ok else 'cancel.png'
    path = f"assets/{name}"
    return QPixmap(path).scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

def crop_to_aspect(img, target_w, target_h):
    h, w = img.shape[:2]
    aspect_img = w / h
    aspect_target = target_w / target_h
    
    if aspect_img > aspect_target:
        new_w = int(h * aspect_target)
        offset = (w - new_w) // 2
        return img[:, offset:offset + new_w]
        
    new_h = int(w / aspect_target)
    offset = (h - new_h) // 2
    return img[offset:offset + new_h, :]

def draw_to_label_with_dpr(frame_bgr, label: QLabel):
    screen = label.screen()
    if not screen:
        screen = QGuiApplication.primaryScreen()
        
    dpr = 1.0
    if screen:
        dpr = float(screen.devicePixelRatio())
        
    tw = max(1, int(label.width() * dpr))
    th = max(1, int(label.height() * dpr))
    
    cropped = crop_to_aspect(frame_bgr, tw, th)
    resized = cv2.resize(cropped, (tw, th), interpolation=cv2.INTER_AREA)
    rgb = cv2.cvtColor(resized, cv2.COLOR_BGR2RGB)
    
    h, w, ch = rgb.shape
    q_img = QImage(rgb.data, w, h, ch * w, QImage.Format_RGB888)
    pm = QPixmap.fromImage(q_img)
    pm.setDevicePixelRatio(dpr)
    label.setPixmap(pm)

def create_line_edit(height=52, font_size=24, padding=12):
    le = QLineEdit()
    le.setFixedHeight(height)
    le.setFont(QFont("Times New Roman", font_size))
    le.setStyleSheet(f"background-color: white; border: none; padding-left: {padding}px;")
    return le

def getbtn_style():
    return f"""
        QPushButton {{ 
            background-color: {COLOR_BTN_BG}; 
            color: white; 
            border-radius: 8px; 
            font-family: "Times New Roman"; 
            font-size: 14px; 
            font-weight: 600; 
        }} 
        QPushButton:hover {{ background-color: {COLOR_GREEN}; }}
    """

# ФАЙЛОВЫЕ ОПЕРАЦИИ И СОХРАНЕНИЕ

def ensure_dirs(base_dir: str):
    ops_dir = os.path.join(CSV_DIRECTORY, "operators")
    os.makedirs(ops_dir, exist_ok=True)
    return ops_dir

def opencv_imread_unicode(filepath):
    data = np.fromfile(filepath, dtype=np.uint8)
    return cv2.imdecode(data, cv2.IMREAD_COLOR)

def opencv_save_jpg(frame_bgr, filepath: str, face_loc=None):
    if frame_bgr is None or not filepath:
        return False
        
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    
    if face_loc:
        x, y, w, h = face_loc
        save_frame = frame_bgr[y:y+h, x:x+w]
    else:
        save_frame = frame_bgr
        
    if save_frame.size == 0:
        return False
        
    success, buffer = cv2.imencode(".jpg", save_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if success:
        with open(filepath, "wb") as f:
            f.write(buffer)
        return True
    return False