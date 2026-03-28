import os
import cv2
import csv
import time
import datetime
import utils

from PyQt5.QtCore import QPoint, Qt, QUrl, QTimer, QThread, pyqtSlot
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPixmap, QPolygon
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QMessageBox, QHBoxLayout, QVBoxLayout, QSpacerItem, QSizePolicy, QGridLayout
)
from analysis_form import SerialWorker

class ShapeWidget(QWidget):
    def __init__(self, shape_type, color, parent=None):
        super().__init__(parent)
        self.shape_type = shape_type
        self.color = color
        self.setFixedSize(40, 40)

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

class ControlForm(QWidget):
    def __init__(self, operator_row: dict = None):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.operator_row = operator_row or {}
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_path = utils._csv_path(self.base_dir)

        self.pulse_norm_min = 60
        self.pulse_norm_max = 80
        self.pulse_crit_threshold = 100
        
        self.eyes_closed_start_time = None
        self.head_tilted_start_time = None
        
        self._load_settings_from_csv()
        
        self.analysis_form = None
        self.instr_form = None

        self.W = 1000
        self.TITLE_H = 30
        self.LINE_H = 4
        self.ORIG_H = 450
        self.H = self.ORIG_H + self.TITLE_H + self.LINE_H
        
        self.setFixedSize(self.W, self.H)
        self.setWindowTitle("НейроБодр - Мониторинг")
        self.setStyleSheet("background-color: #D9D9D9;")

        self.current_pulse_val = 0
        self.current_state = "NORMAL"
        self.start_app_time = datetime.datetime.now()
        self.remaining_seconds = 9 * 3600

        self.player_warning = QMediaPlayer()
        self.playlist_warn = QMediaPlaylist()
        self.playlist_warn.addMedia(QMediaContent(QUrl.fromLocalFile("yellowSound.mp3")))
        self.playlist_warn.setPlaybackMode(QMediaPlaylist.Loop)
        self.player_warning.setPlaylist(self.playlist_warn)

        self.player_alarm = QMediaPlayer()
        self.playlist_alarm = QMediaPlaylist()
        self.playlist_alarm.addMedia(QMediaContent(QUrl.fromLocalFile("redSound.mp3")))
        self.playlist_alarm.setPlaybackMode(QMediaPlaylist.Loop)
        self.player_alarm.setPlaylist(self.playlist_alarm)

        self.video_cap = None
        self.current_frame = None

        self._build_ui()
        self._init_logic()

    def _load_settings_from_csv(self):
        target_id = str(self.operator_row.get("id", ""))
        if not target_id:
            return
            
        with open(self.csv_path, "r", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                if row.get("id") == target_id:
                    p_norm = row.get("pulse_normal", "")
                    
                    if "-" in p_norm:
                        parts = p_norm.split("-")
                        self.pulse_norm_min = int(parts[0])
                        self.pulse_norm_max = int(parts[1])
                    elif p_norm.isdigit():
                        self.pulse_norm_max = int(p_norm)
                    
                    crit_raw = row.get("pulse_threshold_critical", "")
                    if crit_raw.isdigit():
                        self.pulse_crit_threshold = int(crit_raw)
                    break

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_grey = QWidget()
        top_grey.setFixedHeight(self.TITLE_H)
        top_layout = QHBoxLayout(top_grey)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("X")
        self.btn_close.setFixedSize(45, self.TITLE_H)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "color: #FF0000; border: none; font-size: 24px; font-weight: bold;"
        )
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_close)
        
        main_layout.addWidget(top_grey)

        top_line = QFrame()
        top_line.setFixedHeight(self.LINE_H)
        top_line.setStyleSheet("background-color: white;")
        main_layout.addWidget(top_line)

        content_container = QWidget()
        content_container.setStyleSheet("background-color: white;")
        
        content_layout = QVBoxLayout(content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)
        
        main_layout.addWidget(content_container)

        header_row = QWidget()
        header_row.setFixedHeight(120)
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        menu_frame = QFrame(); menu_frame.setStyleSheet("background-color: #D9D9D9;")
        logo_frame = QFrame(); logo_frame.setStyleSheet("background-color: #44CC29;")
        id_frame = QFrame(); id_frame.setStyleSheet("background-color: #D9D9D9;")
        
        header_layout.addWidget(menu_frame, stretch=1)
        header_layout.addWidget(logo_frame, stretch=1)
        header_layout.addWidget(id_frame, stretch=1)
        
        content_layout.addWidget(header_row)

        menu_vbox = QVBoxLayout(menu_frame)
        menu_vbox.setContentsMargins(10, 15, 10, 15)
        
        lbl_menu = QLabel("Меню управления")
        lbl_menu.setAlignment(Qt.AlignCenter)
        lbl_menu.setFont(QFont("Times New Roman", 18))
        menu_vbox.addWidget(lbl_menu)
        
        menu_vbox.addStretch()
        
        btn_hbox = QHBoxLayout()
        b_style = (
            "color: white; border-radius: 18px; "
            "font-family: 'Times New Roman'; font-size: 14px; font-weight: bold;"
        )
        
        self.btn_instr = QPushButton("Инструкция")
        self.btn_instr.setFixedHeight(36)
        self.btn_instr.setStyleSheet(f"QPushButton {{ background-color: #8D3C7F; {b_style} }}")
        self.btn_instr.clicked.connect(self._go_instruction)
        
        self.btn_analysis = QPushButton("Анализ")
        self.btn_analysis.setFixedHeight(36)
        self.btn_analysis.setStyleSheet(f"QPushButton {{ background-color: #8D3C7F; {b_style} }}")
        self.btn_analysis.clicked.connect(self._go_analysis)
        
        self.btn_control = QPushButton("Управление")
        self.btn_control.setFixedHeight(36)
        self.btn_control.setStyleSheet(f"QPushButton {{ background-color: #44CC29; {b_style} }}")
        
        btn_hbox.addWidget(self.btn_instr)
        btn_hbox.addWidget(self.btn_analysis)
        btn_hbox.addWidget(self.btn_control)
        menu_vbox.addLayout(btn_hbox)

        logo_vbox = QVBoxLayout(logo_frame)
        logo_vbox.setContentsMargins(0, 10, 0, 10)
        logo_vbox.setSpacing(5)
        
        lbl_logo = QLabel("НейроБодр")
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setStyleSheet("color: white; font-weight: bold;")
        lbl_logo.setFont(QFont("Times New Roman", 24))
        logo_vbox.addWidget(lbl_logo)
        
        line_layout = QHBoxLayout()
        line_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet("background-color: white;")
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line_layout.addWidget(line, stretch=3) 
        line_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        logo_vbox.addLayout(line_layout)
        
        lbl_desc = QLabel("Программа для мониторинга\nсостояния водителей")
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet("color: white;")
        lbl_desc.setFont(QFont("Times New Roman", 14))
        logo_vbox.addWidget(lbl_desc)

        id_vbox = QVBoxLayout(id_frame)
        id_vbox.setContentsMargins(0, 0, 0, 0)
        id_vbox.setSpacing(0)
        
        lbl_id_title = QLabel("Идентификация")
        lbl_id_title.setFixedHeight(44)
        lbl_id_title.setAlignment(Qt.AlignCenter)
        lbl_id_title.setFont(QFont("Times New Roman", 14))
        id_vbox.addWidget(lbl_id_title)
        
        id_sep = QFrame()
        id_sep.setFixedHeight(4)
        id_sep.setStyleSheet("background-color: white;")
        id_vbox.addWidget(id_sep)
        
        id_data_hbox = QHBoxLayout()
        id_data_hbox.setContentsMargins(20, 10, 20, 10)
        
        lbl_op_status = QLabel("Оператор\nопределен:")
        lbl_op_status.setFont(QFont("Times New Roman", 14))
        
        f_name = self.operator_row.get('first_name', '')
        l_name = self.operator_row.get('last_name', '')
        self.lbl_op_name = QLabel(f"{l_name} {f_name}")
        self.lbl_op_name.setFont(QFont("Times New Roman", 16))
        
        id_data_hbox.addWidget(lbl_op_status)
        id_data_hbox.addStretch()
        id_data_hbox.addWidget(self.lbl_op_name)
        id_vbox.addLayout(id_data_hbox)

        body_row = QWidget()
        body_layout = QHBoxLayout(body_row)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(4)
        
        self.left_col = QFrame()
        self.left_col.setStyleSheet("background-color: #D9D9D9;")
        self.video_col = QFrame()
        self.video_col.setStyleSheet("background-color: #2C2C2C;")
        
        body_layout.addWidget(self.left_col, stretch=1)
        body_layout.addWidget(self.video_col, stretch=2)
        
        content_layout.addWidget(body_row, stretch=1)

        self._build_left_info_panel()
        self._build_video_area()

    def _build_left_info_panel(self):
        left_layout = QVBoxLayout(self.left_col)
        left_layout.setContentsMargins(0, 10, 0, 0)
        left_layout.setSpacing(0)

        font_label = QFont("Times New Roman", 12)
        font_val = QFont("Times New Roman", 12, QFont.Bold)
        font_header = QFont("Times New Roman", 14)
        font_term = QFont("Consolas", 10)

        dt_str = utils._now_date_str() + " / " + utils._now_time_str()
        start_str = self.operator_row.get("software_start_time", utils._now_time_str())

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(15, 0, 15, 10)
        grid_layout.setVerticalSpacing(5)

        lbl_t1 = QLabel("Дата/время:")
        lbl_t1.setFont(font_label)
        self.lbl_dt_val = QLabel(dt_str)
        self.lbl_dt_val.setFont(font_val)
        grid_layout.addWidget(lbl_t1, 0, 0)
        grid_layout.addWidget(self.lbl_dt_val, 0, 1)

        lbl_t2 = QLabel("Время запуска:")
        lbl_t2.setFont(font_label)
        self.lbl_start_val = QLabel(start_str)
        self.lbl_start_val.setFont(font_val)
        grid_layout.addWidget(lbl_t2, 1, 0)
        grid_layout.addWidget(self.lbl_start_val, 1, 1)

        lbl_t3 = QLabel("Состояние оператора:")
        lbl_t3.setFont(font_label)
        self.lbl_state_val = QLabel("НОРМА")
        self.lbl_state_val.setFont(font_val)
        self.lbl_state_val.setStyleSheet("color: #009900;")
        grid_layout.addWidget(lbl_t3, 2, 0)
        grid_layout.addWidget(self.lbl_state_val, 2, 1)
        
        left_layout.addWidget(grid_widget)

        sep1 = QFrame()
        sep1.setFixedHeight(4)
        sep1.setStyleSheet("background-color: white;")
        left_layout.addWidget(sep1)

        lbl_term_head = QLabel("Терминальный блок")
        lbl_term_head.setFixedHeight(30)
        lbl_term_head.setAlignment(Qt.AlignCenter)
        lbl_term_head.setFont(font_header)
        left_layout.addWidget(lbl_term_head)

        sep2 = QFrame()
        sep2.setFixedHeight(4)
        sep2.setStyleSheet("background-color: white;")
        left_layout.addWidget(sep2)

        term_container = QWidget()
        term_layout = QVBoxLayout(term_container)
        term_layout.setContentsMargins(3, 0, 3, 0)
        
        term_box = QFrame()
        term_box.setStyleSheet("background-color: #2C2C2C;")
        term_box_layout = QVBoxLayout(term_box)
        
        self.lbl_term_text = QLabel("Состояние нормальное\nПульс --")
        self.lbl_term_text.setStyleSheet("color: white; background: transparent;")
        self.lbl_term_text.setFont(font_term)
        self.lbl_term_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        term_box_layout.addWidget(self.lbl_term_text)
        
        term_layout.addWidget(term_box)
        left_layout.addWidget(term_container, stretch=1)

        sep3 = QFrame()
        sep3.setFixedHeight(4)
        sep3.setStyleSheet("background-color: white;")
        left_layout.addWidget(sep3)

        lbl_time_head = QLabel("Допустимое время")
        lbl_time_head.setFixedHeight(30)
        lbl_time_head.setAlignment(Qt.AlignCenter)
        lbl_time_head.setFont(font_header)
        left_layout.addWidget(lbl_time_head)

        sep4 = QFrame()
        sep4.setFixedHeight(4)
        sep4.setStyleSheet("background-color: white;")
        left_layout.addWidget(sep4)

        self.lbl_clock = QLabel("09:00")
        self.lbl_clock.setAlignment(Qt.AlignCenter)
        self.lbl_clock.setFont(QFont("Times New Roman", 42, QFont.Bold))
        left_layout.addWidget(self.lbl_clock, stretch=1)

    def _build_video_area(self):
        video_layout = QVBoxLayout(self.video_col)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_label = QLabel()
        self.video_label.setStyleSheet("background-color: #2C2C2C;")
        video_layout.addWidget(self.video_label)

        self.video_cap = cv2.VideoCapture("videoBG.mp4")
        self.timer_video = QTimer(self)
        self.timer_video.timeout.connect(self._update_video_frame)
        self.timer_video.start(33)

        overlay_layout = QVBoxLayout(self.video_label)
        overlay_layout.setContentsMargins(0, 0, 0, 0)
        overlay_layout.setSpacing(0)

        top_row_layout = QHBoxLayout()
        top_row_layout.setContentsMargins(0, 0, 0, 0)
        top_row_layout.setSpacing(0)

        top_strip = QFrame()
        top_strip.setFixedHeight(70)
        top_strip.setStyleSheet("background-color: rgba(255, 255, 255, 100); border: none;")
        
        strip_layout = QHBoxLayout(top_strip)
        strip_layout.setContentsMargins(15, 0, 20, 0)
        strip_layout.setSpacing(15)

        self.lbl_sq_green = ShapeWidget("circle", "#7CE4D5")
        self.lbl_sq_yellow = ShapeWidget("triangle", "#FFD700")
        self.lbl_sq_red = ShapeWidget("square", "#FF0000")

        strip_layout.addWidget(self.lbl_sq_green)
        strip_layout.addWidget(self.lbl_sq_yellow)
        strip_layout.addWidget(self.lbl_sq_red)

        strip_layout.addStretch()

        lbl_pulse = QLabel("Пульс:")
        lbl_pulse.setFont(QFont("Times New Roman", 28, QFont.Bold))
        lbl_pulse.setStyleSheet("color: #2C2C2C; background: transparent;")
        strip_layout.addWidget(lbl_pulse)

        self.lbl_pulse_overlay = QLabel("--")
        self.lbl_pulse_overlay.setFont(QFont("Times New Roman", 42, QFont.Bold))
        self.lbl_pulse_overlay.setStyleSheet("color: #009900; background: transparent;")
        strip_layout.addWidget(self.lbl_pulse_overlay)
        
        strip_layout.addStretch()

        face_frame = QFrame()
        face_frame.setFixedSize(190, 190)
        face_frame.setStyleSheet("background-color: white;")
        
        face_layout = QVBoxLayout(face_frame)
        face_layout.setContentsMargins(2, 2, 2, 2)
        
        self.lbl_cam_feed = QLabel()
        self.lbl_cam_feed.setStyleSheet("background-color: #2C2C2C;")
        face_layout.addWidget(self.lbl_cam_feed)

        top_row_layout.addWidget(top_strip, stretch=1, alignment=Qt.AlignTop)
        top_row_layout.addWidget(face_frame, alignment=Qt.AlignTop)

        overlay_layout.addLayout(top_row_layout)
        overlay_layout.addStretch()

    def _init_logic(self):
        self.thread_pulse = QThread()
        self.worker_pulse = SerialWorker(port="COM5")
        self.worker_pulse.moveToThread(self.thread_pulse)
        self.thread_pulse.started.connect(self.worker_pulse.run)
        self.worker_pulse.data_received.connect(self._on_pulse_data)
        self.thread_pulse.start()

        self.timer_main = QTimer(self)
        self.timer_main.timeout.connect(self._update_time_logic)
        self.timer_main.start(1000)

        self.cap = cv2.VideoCapture(0)
        
        face_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        eye_path = cv2.data.haarcascades + 'haarcascade_eye.xml'
        self.face_cascade = cv2.CascadeClassifier(face_path)
        self.eye_cascade = cv2.CascadeClassifier(eye_path)
        
        self.timer_cam = QTimer(self)
        self.timer_cam.timeout.connect(self._process_camera_frame)
        self.timer_cam.start(30)
        
        self._update_time_ui()

    def _update_video_frame(self):
        if not self.video_cap or not self.video_cap.isOpened():
            return
            
        ret, frame = self.video_cap.read()
        if not ret:
            self.video_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.video_cap.read()
            if not ret:
                return

        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = frame_rgb.shape
        bytes_per_line = ch * w
        
        q_img = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)
        pixmap = QPixmap.fromImage(q_img)
        
        self.video_label.setPixmap(
            pixmap.scaled(self.video_label.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        )

    @pyqtSlot(str, str, str)
    def _on_pulse_data(self, status_conn, status_pulse, pulse_str):
        self.current_pulse_val = int(pulse_str) if pulse_str.isdigit() else 0
        self.lbl_pulse_overlay.setText(pulse_str if pulse_str.isdigit() else "--")
        self._check_status()

    def _process_camera_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
            
        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        detected_eyes = False
        detected_face = False

        if len(faces) > 0:
            detected_face = True
            faces_sorted = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
            x, y, w, h = faces_sorted[0]
            
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            
            roi_gray = gray[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 10, minSize=(20, 20))
            
            if len(eyes) > 0:
                detected_eyes = True
                for ex, ey, ew, eh in eyes:
                    cv2.rectangle(frame[y:y+h, x:x+w], (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)

        curr_time = time.time()
        
        if detected_face and not detected_eyes:
            if not self.eyes_closed_start_time:
                self.eyes_closed_start_time = curr_time
        elif not detected_face:
            if not self.eyes_closed_start_time:
                self.eyes_closed_start_time = curr_time
        else:
            self.eyes_closed_start_time = None

        if not detected_face:
            if not self.head_tilted_start_time:
                self.head_tilted_start_time = curr_time
        else:
            self.head_tilted_start_time = None

        utils._draw_to_label_with_dpr(frame, self.lbl_cam_feed)
        self._check_status()

    def _check_status(self):
        curr_time = time.time()
        
        sec_closed = 0
        if self.eyes_closed_start_time:
            sec_closed = curr_time - self.eyes_closed_start_time
            
        sec_tilted = 0
        if self.head_tilted_start_time:
            sec_tilted = curr_time - self.head_tilted_start_time
        
        p = self.current_pulse_val
        new_state = "NORMAL"

        is_crit_pulse = p > 0 and (p <= self.pulse_norm_min * 0.7 or p >= self.pulse_crit_threshold)
        is_warn_pulse = p > 0 and (p <= self.pulse_norm_min * 0.8 or (p >= self.pulse_norm_max * 1.2 and p < self.pulse_crit_threshold))

        if is_crit_pulse or sec_closed > 7.0 or sec_tilted > 7.0:
            new_state = "CRITICAL"
        elif is_warn_pulse or sec_closed > 4.0 or sec_tilted > 4.0:
            new_state = "WARNING"

        if new_state != self.current_state:
            self.current_state = new_state
            self._update_ui_state()
            self._update_csv_log()
        
        p_str = str(self.current_pulse_val) if self.current_pulse_val > 0 else "--"
        
        if self.current_state == "NORMAL":
            self.lbl_term_text.setText(f"Состояние нормальное\nПульс {p_str}")
        elif self.current_state == "WARNING":
            msg = (f"Состояние оператора выходит за пределы\n«ВНИМАНИЕ»\n"
                   f"Пульс {p_str}\nЗапуск звукового оповещения «ВНИМАНИЕ»")
            self.lbl_term_text.setText(msg)
        else:
            msg = f"Состояние критичное!\nПульс {p_str}\nЗапуск звукового оповещения!"
            self.lbl_term_text.setText(msg)

    def _update_ui_state(self):
        self.player_warning.stop()
        self.player_alarm.stop()
        
        states = {
            "NORMAL": ("НОРМА", "#009900", "#7CE4D5", "#C7C7C7", "#C7C7C7", None),
            "WARNING": ("ВНИМАНИЕ", "#FFD700", "#C7C7C7", "#FFD700", "#C7C7C7", self.player_warning),
            "CRITICAL": ("КРИТИЧНО!", "#FF0000", "#C7C7C7", "#C7C7C7", "#FF0000", self.player_alarm)
        }
        
        text, color, c_green, c_yellow, c_red, player = states[self.current_state]
        
        self.lbl_state_val.setText(text)
        self.lbl_state_val.setStyleSheet(f"color: {color};")
        self.lbl_pulse_overlay.setStyleSheet(f"color: {color}; background: transparent;")
        
        self.lbl_sq_green.set_color(c_green)
        self.lbl_sq_yellow.set_color(c_yellow)
        self.lbl_sq_red.set_color(c_red)
        
        if player:
            player.play()

    def _update_time_logic(self):
        dt_text = utils._now_date_str() + " / " + utils._now_time_str()
        self.lbl_dt_val.setText(dt_text)
        
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            h = self.remaining_seconds // 3600
            m = (self.remaining_seconds % 3600) // 60
            self.lbl_clock.setText(f"{h:02d}:{m:02d}")
        else:
            self.timer_main.stop()
            self.lbl_clock.setText("00:00")
            QMessageBox.information(self, "Конец", "Время вышло!")
            
        self._update_csv_log()

    def _update_time_ui(self):
        dt_text = utils._now_date_str() + " / " + utils._now_time_str()
        self.lbl_dt_val.setText(dt_text)

    def _update_csv_log(self):
        target_id = str(self.operator_row.get("id", ""))
        if not target_id:
            return

        delta = datetime.datetime.now() - self.start_app_time
        drive_str = utils._seconds_to_hms(delta.total_seconds())
        
        updates = {
            "current_pulse": str(self.current_pulse_val), 
            "operator_status": self.current_state, 
            "drive_duration": drive_str
        }
        
        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames) if reader.fieldnames else []
                rows = list(reader)

            for key in updates:
                if key not in fieldnames:
                    fieldnames.append(key)

            for row in rows:
                if row.get("id") == target_id:
                    row.update(updates)
                    break
            
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(rows)
        except Exception as e:
            print(f"Ошибка обновления CSV: {e}")

    def _go_instruction(self):
        self.close()
        from instruction_form import InstructionForm
        if not self.instr_form:
            self.instr_form = InstructionForm(self.operator_row)
        self.instr_form.show()

    def _go_analysis(self):
        self.close()
        from analysis_form import AnalysisForm
        if not self.analysis_form:
            self.analysis_form = AnalysisForm(self.operator_row)
        self.analysis_form.show()

    def closeEvent(self, event):
        self._update_csv_log()
        
        if hasattr(self, 'worker_pulse'):
            self.worker_pulse.stop()
            
        if hasattr(self, 'thread_pulse'):
            self.thread_pulse.quit()
            self.thread_pulse.wait()
            
        self.timer_main.stop()
        self.timer_cam.stop()
        self.timer_video.stop()
        
        if hasattr(self, 'cap') and self.cap.isOpened():
            self.cap.release()
            
        if self.video_cap:
            self.video_cap.release()
            
        self.player_warning.stop()
        self.player_alarm.stop()
        
        super().closeEvent(event)