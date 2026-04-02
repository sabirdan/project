import os
import csv
import cv2
import numpy as np
from datetime import datetime
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtMultimedia import *

COLOR_BG = "#D9D9D9"
COLOR_BTN_BG = "#2C2C2C"
COLOR_GREEN = "#44CC29"
COLOR_DISABLED = "#C7C7C7"

CSV_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
CASCADE_PATH = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
FACE_CASCADE = cv2.CascadeClassifier(CASCADE_PATH)

def csv_path():
    return os.path.join(CSV_DIRECTORY, "operators_db.csv")

def ensure_csv(csv_file_path):
    if not os.path.exists(csv_file_path):
        with open(csv_file_path, "w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["id", "last_name", "first_name", "middle_name", "age", "date", "time", "software_start_time", "drive_duration"])

def next_id(csv_file_path):
    with open(csv_file_path, "r", encoding="utf-8") as file:
        ids_list = [int(row["id"]) for row in csv.DictReader(file) if row.get("id")]
        if ids_list:
            return max(ids_list) + 1
        return 1

def id_str(number):
    return str(number).zfill(5)

def find_operator_by_id(csv_file_path, operator_id):
    with open(csv_file_path, "r", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            if int(row["id"]) == operator_id:
                return row
    return None

def update_db(csv_file_path, operator_id, data_dictionary):
    with open(csv_file_path, "r", encoding="utf-8") as file:
        reader = csv.DictReader(file)
        fields = list(reader.fieldnames)
        rows_list = list(reader)

    for key in data_dictionary:
        if key not in fields:
            fields.append(key)

    for row in rows_list:
        if str(row["id"]) == str(operator_id):
            row.update(data_dictionary)

    with open(csv_file_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows_list)

def now_date_str():
    return datetime.now().strftime("%d.%m.%Y")

def now_time_str():
    return datetime.now().strftime("%H:%M:%S")

def parse_hms_to_seconds(time_string):
    hours, minutes, seconds = map(int, time_string.split(":"))
    return hours * 3600 + minutes * 60 + seconds

def seconds_to_hms(total_seconds):
    total_seconds = max(0, int(total_seconds))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

def process_face(video_frame, draw_rectangle=False, rectangle_color=(0, 255, 0)):
    if video_frame is None:
        return None, None
    
    gray_frame = cv2.cvtColor(video_frame, cv2.COLOR_BGR2GRAY)
    faces = FACE_CASCADE.detectMultiScale(gray_frame, 1.3, 5, minSize=(100, 100))
    
    if len(faces) > 0:
        x, y, width, height = max(faces, key=lambda face: face[2] * face[3])
        if draw_rectangle:
            cv2.rectangle(video_frame, (x, y), (x + width, y + height), rectangle_color, 2)
        return gray_frame[y:y + height, x:x + width], (x, y, width, height)
    
    return None, None

def cv_compare_faces(reference_gray, live_gray, threshold=0.6):
    if reference_gray is None or live_gray is None:
        return False
    
    reference_resized = cv2.resize(reference_gray, (150, 150))
    live_resized = cv2.resize(live_gray, (150, 150))
    match_result = cv2.matchTemplate(reference_resized, live_resized, cv2.TM_CCOEFF_NORMED)
    return float(match_result[0][0]) >= threshold

class BaseWindow(QWidget):
    def __init__(self, window_width, window_height, window_title):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(window_width, window_height)
        self.setWindowTitle(window_title)
        self.setStyleSheet(f"background-color: {COLOR_BG};")
        
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(0)
        
        self.button_close = QPushButton("X")
        self.button_close.setFixedSize(45, 30)
        self.button_close.setCursor(Qt.PointingHandCursor)
        self.button_close.setStyleSheet("color: red; border: none; font: bold 24px;")
        self.button_close.clicked.connect(self.close)
        self.main_layout.addWidget(self.button_close, alignment=Qt.AlignRight)
        
        line = QFrame()
        line.setFixedHeight(4)
        line.setStyleSheet("background-color: white;")
        self.main_layout.addWidget(line)
        
        self.content_container = QWidget()
        self.main_layout.addWidget(self.content_container)

class ShapeWidget(QWidget):
    def __init__(self, shape_type, fill_color, widget_size=40):
        super().__init__()
        self.shape_type = shape_type
        self.fill_color = fill_color
        self.setFixedSize(widget_size, widget_size)

    def set_color(self, new_color):
        self.fill_color = new_color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(self.fill_color))
        drawing_rect = self.rect()
        
        draw_actions = {
            "circle": lambda: painter.drawEllipse(drawing_rect),
            "square": lambda: painter.drawRect(drawing_rect),
            "triangle": lambda: painter.drawPolygon(QPolygon([
                QPoint(drawing_rect.width() // 2, 0), 
                drawing_rect.bottomLeft(), 
                drawing_rect.bottomRight()
            ]))
        }
        
        if self.shape_type in draw_actions:
            draw_actions[self.shape_type]()

def create_label(text, font_size=14, color=None, align=None):
    label_widget = QLabel(text)
    custom_font = QFont("Times New Roman", font_size)
    label_widget.setFont(custom_font)
    
    if color:
        label_widget.setStyleSheet(f"color: {color};")
    if align:
        label_widget.setAlignment(align)
    return label_widget

def make_icon(is_ok, icon_size=28):
    icon_map = {True: "assets/accept.png", False: "assets/cancel.png"}
    pixmap = QPixmap(icon_map[is_ok])
    return pixmap.scaled(icon_size, icon_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

def draw_to_label(video_frame, target_label):
    resized_frame = cv2.resize(video_frame, (target_label.width(), target_label.height()))
    rgb_frame = cv2.cvtColor(resized_frame, cv2.COLOR_BGR2RGB)
    qt_image = QImage(rgb_frame.data, rgb_frame.shape[1], rgb_frame.shape[0], rgb_frame.shape[1] * 3, QImage.Format_RGB888)
    target_label.setPixmap(QPixmap.fromImage(qt_image))

def create_line_edit(field_height=52, font_size=24, text_padding=12):
    line_edit_widget = QLineEdit()
    line_edit_widget.setFixedHeight(field_height)
    line_edit_widget.setFont(QFont("Times New Roman", font_size))
    line_edit_widget.setStyleSheet(f"background-color: white; border: none; padding-left: {text_padding}px;")
    return line_edit_widget

def get_button_style():
    base_style = f"QPushButton {{ background-color: {COLOR_BTN_BG}; color: white; border-radius: 8px; font: bold 14px 'Times New Roman';}} "
    hover_style = f"QPushButton:hover {{ background-color: {COLOR_GREEN}; }} "
    disabled_style = f"QPushButton:disabled {{ background-color: {COLOR_DISABLED}; color: gray; }}"
    return base_style + hover_style + disabled_style

def create_button(text, button_width=110, button_height=36, callback_function=None):
    button_widget = QPushButton(text)
    button_widget.setFixedSize(button_width, button_height)
    
    button_widget.setCursor(Qt.PointingHandCursor)
    button_widget.setStyleSheet(get_button_style())
    
    if callback_function:
        button_widget.clicked.connect(callback_function)
    return button_widget

def ensure_dirs():
    target_directory = os.path.join(CSV_DIRECTORY, "operators")
    os.makedirs(target_directory, exist_ok=True)
    return target_directory

def opencv_imread_unicode(file_path):
    file_data = np.fromfile(file_path, dtype=np.uint8)
    return cv2.imdecode(file_data, cv2.IMREAD_COLOR)

def opencv_save_jpg(frame_bgr, file_path, face_location=None):
    directory = os.path.dirname(file_path)
    os.makedirs(directory, exist_ok=True)
    
    if face_location:
        x, y, width, height = face_location
        face_crop = frame_bgr[y:y + height, x:x + width]
    else:
        face_crop = frame_bgr
        
    if face_crop.size == 0:
        return False
        
    success, image_buffer = cv2.imencode(".jpg", face_crop, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    if success:
        with open(file_path, "wb") as file:
            file.write(image_buffer)
        return True
    return False