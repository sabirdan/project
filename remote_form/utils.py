import os
from PyQt5.QtCore import Qt, QPoint
from PyQt5.QtGui import QPainter, QBrush, QColor, QPolygon, QFont
from PyQt5.QtWidgets import QLabel, QWidget, QVBoxLayout, QHBoxLayout, QPushButton

COLOR_BG = "#D9D9D9"
COLOR_RED = "#FF0000"
COLOR_BTN_BG = "#2C2C2C"
COLOR_GREEN = "#44CC29"
COLOR_NORM_TEXT = "#009900"
COLOR_WARN = "#FFD700"
COLOR_CIRCLE_GREEN = "#7CE4D5"
COLOR_SHAPE_OFF = "#C7C7C7"

CSV_DIRECTORY = r"C:\Users\user\Desktop\Профессионалы межрегион 2026\project-championat"

def _csv_path(base_dir: str = None):
    return os.path.join(CSV_DIRECTORY, "operators_db.csv")

def _id_str(n: int) -> str:
    return str(n).zfill(5)

def _parse_hms_to_seconds(s: str) -> int:
    parts = (s or "00:00:00").strip().split(":")
    if len(parts) == 3:
        return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
    return 0

def _ensure_dirs(base_dir: str):
    ops_dir = os.path.join(CSV_DIRECTORY, "operators")
    os.makedirs(ops_dir, exist_ok=True)
    return ops_dir

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
            f"color: {COLOR_RED}; background: transparent; border: none; font-size: 24px; font-weight: bold;"
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

def create_line_edit(height=52, font_size=24, padding=12):
    le = QLineEdit()
    le.setFixedHeight(height)
    le.setFont(QFont("Times New Roman", font_size))
    le.setStyleSheet(f"background-color: white; border: none; padding-left: {padding}px;")
    return le

def get_btn_style():
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