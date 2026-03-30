import csv

import cv2
import time
import datetime

from PyQt5.QtCore import Qt, QUrl, QTimer, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist
from PyQt5.QtGui import QFont, QImage, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QFrame, QMessageBox, QHBoxLayout, 
    QVBoxLayout, QSpacerItem, QSizePolicy, QGridLayout, QLabel
)

from utils import (
    csv_path, now_date_str, now_time_str, seconds_to_hms, draw_to_label_with_dpr,
    BaseWindow, ShapeWidget, create_label, update_db, process_face,
    COLOR_BG, COLOR_GREEN, COLOR_BTN_BG, COLOR_DISABLED
)
from analysis_form import SerialWorker

class ControlForm(BaseWindow):
    sig_go_instruction = pyqtSignal(dict)
    sig_go_analysis = pyqtSignal(dict)

    def __init__(self, operator_row: dict = None):
        super().__init__(1000, 484, "НейроБодр - Мониторинг")
        
        self.operator_row = operator_row or {}
        self.csv_path = csv_path()

        self.pulse_norm_min = 60
        self.pulse_norm_max = 80
        self.pulse_crit_threshold = 100
        
        self.eyes_closed_start_time = None
        self.head_tilted_start_time = None
        
        self.load_settings_from_csv()
        
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

        content_layout = QVBoxLayout(self.content_container)
        self.content_container.setStyleSheet("background-color: white;")
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(4)

        self.build_ui(content_layout)
        self.init_logic()

    def load_settings_from_csv(self):
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

    def build_ui(self, parent_layout):
        header_row = QWidget()
        header_row.setFixedHeight(120)
        header_row.setStyleSheet("background-color: white;")
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        
        menu_frame = QFrame()
        menu_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        logo_frame = QFrame()
        logo_frame.setStyleSheet(f"background-color: {COLOR_GREEN};")
        id_frame = QFrame()
        id_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        
        header_layout.addWidget(menu_frame, stretch=1)
        header_layout.addWidget(logo_frame, stretch=1)
        header_layout.addWidget(id_frame, stretch=1)
        
        parent_layout.addWidget(header_row)

        menu_vbox = QVBoxLayout(menu_frame)
        menu_vbox.setContentsMargins(10, 15, 10, 15)
        
        lbl_menu = create_label("Меню управления", 18, align=Qt.AlignCenter)
        menu_vbox.addWidget(lbl_menu)
        menu_vbox.addStretch()
        
        btn_hbox = QHBoxLayout()
        b_style = "color: white; border-radius: 18px; font-family: Times New Roman; font-size: 14px; font-weight: bold;"
        
        self.btn_instr = QPushButton("Инструкция")
        self.btn_instr.setFixedHeight(36)
        self.btn_instr.setStyleSheet(f"QPushButton {{ background-color: purple; {b_style} }}")
        self.btn_instr.clicked.connect(self.go_instruction)
        
        self.btn_analysis = QPushButton("Анализ")
        self.btn_analysis.setFixedHeight(36)
        self.btn_analysis.setStyleSheet(f"QPushButton {{ background-color: purple; {b_style} }}")
        self.btn_analysis.clicked.connect(self.go_analysis)
        
        self.btn_control = QPushButton("Управление")
        self.btn_control.setFixedHeight(36)
        self.btn_control.setStyleSheet(f"QPushButton {{ background-color: {COLOR_GREEN}; {b_style} }}")
        
        btn_hbox.addWidget(self.btn_instr)
        btn_hbox.addWidget(self.btn_analysis)
        btn_hbox.addWidget(self.btn_control)
        menu_vbox.addLayout(btn_hbox)

        logo_vbox = QVBoxLayout(logo_frame)
        logo_vbox.setContentsMargins(0, 10, 0, 10)
        logo_vbox.setSpacing(5)
        
        lbl_logo = create_label("НейроБодр", 24, bold=True, color="white", align=Qt.AlignCenter)
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
        
        lbl_desc = create_label("Программа для мониторинга\nсостояния водителей", 14, color="white", align=Qt.AlignCenter)
        logo_vbox.addWidget(lbl_desc)

        id_vbox = QVBoxLayout(id_frame)
        id_vbox.setContentsMargins(0, 0, 0, 0)
        id_vbox.setSpacing(0)
        
        lbl_id_title = create_label("Идентификация", 14, align=Qt.AlignCenter)
        lbl_id_title.setFixedHeight(44)
        id_vbox.addWidget(lbl_id_title)
        
        id_sep = QFrame()
        id_sep.setFixedHeight(4)
        id_sep.setStyleSheet("background-color: white;")
        id_vbox.addWidget(id_sep)
        
        id_data_hbox = QHBoxLayout()
        id_data_hbox.setContentsMargins(20, 10, 20, 10)
        
        lbl_op_status = create_label("Оператор\nопределен:", 14)
        
        f_name = self.operator_row.get("first_name", "")
        l_name = self.operator_row.get("last_name", "")
        self.lbl_op_name = create_label(f"{l_name} {f_name}", 16)
        
        id_data_hbox.addWidget(lbl_op_status)
        id_data_hbox.addStretch()
        id_data_hbox.addWidget(self.lbl_op_name)
        id_vbox.addLayout(id_data_hbox)

        body_row = QWidget()
        body_row.setStyleSheet("background-color: white;")
        body_layout = QHBoxLayout(body_row)
        body_layout.setContentsMargins(0, 0, 0, 0)
        body_layout.setSpacing(4)
        
        self.left_col = QFrame()
        self.left_col.setStyleSheet(f"background-color: {COLOR_BG};")
        self.video_col = QFrame()
        self.video_col.setStyleSheet(f"background-color: {COLOR_BTN_BG};")
        
        body_layout.addWidget(self.left_col, stretch=1)
        body_layout.addWidget(self.video_col, stretch=2)
        
        parent_layout.addWidget(body_row, stretch=1)

        self.build_left_info_panel()
        self.build_video_area()

    def build_left_info_panel(self):
        left_layout = QVBoxLayout(self.left_col)
        left_layout.setContentsMargins(0, 10, 0, 0)
        left_layout.setSpacing(0)

        dt_str = now_date_str() + " / " + now_time_str()
        start_str = self.operator_row.get("software_start_time", now_time_str())

        grid_widget = QWidget()
        grid_layout = QGridLayout(grid_widget)
        grid_layout.setContentsMargins(15, 0, 15, 10)
        grid_layout.setVerticalSpacing(5)

        lbl_t1 = create_label("Дата/время:", 12)
        self.lbl_dt_val = create_label(dt_str, 12, bold=True)
        grid_layout.addWidget(lbl_t1, 0, 0)
        grid_layout.addWidget(self.lbl_dt_val, 0, 1)

        lbl_t2 = create_label("Время запуска:", 12)
        self.lbl_start_val = create_label(start_str, 12, bold=True)
        grid_layout.addWidget(lbl_t2, 1, 0)
        grid_layout.addWidget(self.lbl_start_val, 1, 1)

        lbl_t3 = create_label("Состояние оператора:", 12)
        self.lbl_state_val = create_label("НОРМА", 12, bold=True, color="green")
        grid_layout.addWidget(lbl_t3, 2, 0)
        grid_layout.addWidget(self.lbl_state_val, 2, 1)
        
        left_layout.addWidget(grid_widget)

        sep1 = QFrame()
        sep1.setFixedHeight(4)
        sep1.setStyleSheet("background-color: white;")
        left_layout.addWidget(sep1)

        lbl_term_head = create_label("Терминальный блок", 14, align=Qt.AlignCenter)
        lbl_term_head.setFixedHeight(30)
        left_layout.addWidget(lbl_term_head)

        sep2 = QFrame()
        sep2.setFixedHeight(4)
        sep2.setStyleSheet("background-color: white;")
        left_layout.addWidget(sep2)

        term_container = QWidget()
        term_layout = QVBoxLayout(term_container)
        term_layout.setContentsMargins(3, 0, 3, 0)
        
        term_box = QFrame()
        term_box.setStyleSheet(f"background-color: {COLOR_BTN_BG};")
        term_box_layout = QVBoxLayout(term_box)
        
        self.lbl_term_text = create_label("Состояние нормальное\nПульс --", 10, color="white", align=Qt.AlignTop | Qt.AlignLeft)
        self.lbl_term_text.setFont(QFont("Consolas", 10))
        term_box_layout.addWidget(self.lbl_term_text)
        
        term_layout.addWidget(term_box)
        left_layout.addWidget(term_container, stretch=1)

        sep3 = QFrame()
        sep3.setFixedHeight(4)
        sep3.setStyleSheet("background-color: white;")
        left_layout.addWidget(sep3)

        lbl_time_head = create_label("Допустимое время", 14, align=Qt.AlignCenter)
        lbl_time_head.setFixedHeight(30)
        left_layout.addWidget(lbl_time_head)

        sep4 = QFrame()
        sep4.setFixedHeight(4)
        sep4.setStyleSheet("background-color: white;")
        left_layout.addWidget(sep4)

        self.lbl_clock = create_label("09:00", 42, bold=True, align=Qt.AlignCenter)
        left_layout.addWidget(self.lbl_clock, stretch=1)

    def build_video_area(self):
        video_layout = QVBoxLayout(self.video_col)
        video_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_label = QLabel()
        self.video_label.setStyleSheet(f"background-color: {COLOR_BTN_BG};")
        video_layout.addWidget(self.video_label)

        self.video_cap = cv2.VideoCapture("videoBG.mp4")
        self.timer_video = QTimer(self)
        self.timer_video.timeout.connect(self.update_video_frame)
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

        self.lbl_sq_green = ShapeWidget("circle", "turquoise")
        self.lbl_sq_yellow = ShapeWidget("triangle", "gold")
        self.lbl_sq_red = ShapeWidget("square", "red")

        strip_layout.addWidget(self.lbl_sq_green)
        strip_layout.addWidget(self.lbl_sq_yellow)
        strip_layout.addWidget(self.lbl_sq_red)

        strip_layout.addStretch()

        lbl_pulse = create_label("Пульс:", 28, bold=True, color=COLOR_BTN_BG)
        lbl_pulse.setStyleSheet("background: transparent;")
        strip_layout.addWidget(lbl_pulse)

        self.lbl_pulse_overlay = create_label("--", 42, bold=True, color="green")
        self.lbl_pulse_overlay.setStyleSheet("background: transparent;")
        strip_layout.addWidget(self.lbl_pulse_overlay)
        
        strip_layout.addStretch()

        face_frame = QFrame()
        face_frame.setFixedSize(190, 190)
        face_frame.setStyleSheet("background-color: white;")
        
        face_layout = QVBoxLayout(face_frame)
        face_layout.setContentsMargins(2, 2, 2, 2)
        
        self.lbl_cam_feed = QLabel()
        self.lbl_cam_feed.setStyleSheet(f"background-color: {COLOR_BTN_BG};")
        face_layout.addWidget(self.lbl_cam_feed)

        top_row_layout.addWidget(top_strip, stretch=1, alignment=Qt.AlignTop)
        top_row_layout.addWidget(face_frame, alignment=Qt.AlignTop)

        overlay_layout.addLayout(top_row_layout)
        overlay_layout.addStretch()

    def init_logic(self):
        self.thread_pulse = QThread()
        self.worker_pulse = SerialWorker(port="COM5")
        self.worker_pulse.moveToThread(self.thread_pulse)
        self.thread_pulse.started.connect(self.worker_pulse.run)
        self.worker_pulse.data_received.connect(self.on_pulse_data)
        self.thread_pulse.start()

        self.timer_main = QTimer(self)
        self.timer_main.timeout.connect(self.update_time_logic)
        self.timer_main.start(1000)

        self.cap = cv2.VideoCapture(0)
        
        face_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        eye_path = cv2.data.haarcascades + "haarcascade_eye.xml"
        self.eye_cascade = cv2.CascadeClassifier(eye_path)
        
        self.timer_cam = QTimer(self)
        self.timer_cam.timeout.connect(self.process_camera_frame)
        self.timer_cam.start(30)
        
        self.update_time_ui()

    def update_video_frame(self):
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
    def on_pulse_data(self, status_conn, status_pulse, pulse_str):
        self.current_pulse_val = int(pulse_str) if pulse_str.isdigit() else 0
        self.lbl_pulse_overlay.setText(pulse_str if pulse_str.isdigit() else "--")
        self.check_status()

    def process_camera_frame(self):
        ret, frame = self.cap.read()
        if not ret:
            return
            
        frame = cv2.flip(frame, 1)
        
        roi_gray, face_loc = process_face(frame, draw=True, color=(0, 255, 0))
        
        detected_face = face_loc is not None
        detected_eyes = False

        if detected_face:
            x, y, w, h = face_loc
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

        draw_to_label_with_dpr(frame, self.lbl_cam_feed)
        self.check_status()

    def check_status(self):
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
            self.update_ui_state()
            self.update_csv_log()
        
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

    def update_ui_state(self):
        self.player_warning.stop()
        self.player_alarm.stop()
        
        states = {
            "NORMAL": ("НОРМА", "green", "turquoise", COLOR_DISABLED, COLOR_DISABLED, None),
            "WARNING": ("ВНИМАНИЕ", "gold", COLOR_DISABLED, "gold", COLOR_DISABLED, self.player_warning),
            "CRITICAL": ("КРИТИЧНО!", "red", COLOR_DISABLED, COLOR_DISABLED, "red", self.player_alarm)
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

    def update_time_logic(self):
        dt_text = now_date_str() + " / " + now_time_str()
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
            
        self.update_csv_log()

    def update_time_ui(self):
        dt_text = now_date_str() + " / " + now_time_str()
        self.lbl_dt_val.setText(dt_text)

    def update_csv_log(self):
        target_id = self.operator_row.get("id", "")
        if not target_id:
            return

        delta = datetime.datetime.now() - self.start_app_time
        drive_str = seconds_to_hms(delta.total_seconds())
        
        updates = {
            "current_pulse": str(self.current_pulse_val), 
            "operator_status": self.current_state, 
            "drive_duration": drive_str
        }
        
        try:
            update_db(self.csv_path, target_id, updates)
        except Exception as e:
            print(f"Ошибка обновления CSV: {e}")

    def go_instruction(self):
        self.sig_go_instruction.emit(self.operator_row)
        self.hide()

    def go_analysis(self):
        self.sig_go_analysis.emit(self.operator_row)
        self.hide()

    def closeEvent(self, event):
        self.update_csv_log()
        
        if hasattr(self, "worker_pulse"):
            self.worker_pulse.stop()
            
        if hasattr(self, "thread_pulse"):
            self.thread_pulse.quit()
            self.thread_pulse.wait()
            
        self.timer_main.stop()
        self.timer_cam.stop()
        self.timer_video.stop()
        
        if hasattr(self, "cap") and self.cap.isOpened():
            self.cap.release()
            
        if self.video_cap:
            self.video_cap.release()
            
        self.player_warning.stop()
        self.player_alarm.stop()
        
        super().closeEvent(event)