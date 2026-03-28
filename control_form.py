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
    QWidget, QLabel, QPushButton, QFrame, QMessageBox, QHBoxLayout
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
        self.HEADER_H = 120
        self.GRID_T = 4
        
        self.Y_OFFSET = self.TITLE_H + self.LINE_H
        self.ORIG_H = 450
        self.H = self.ORIG_H + self.Y_OFFSET
        self.BODY_H = self.ORIG_H - self.HEADER_H
        
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
        top_grey = QWidget(self)
        top_grey.setGeometry(0, 0, self.W, self.TITLE_H)
        top_layout = QHBoxLayout(top_grey)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("X", top_grey)
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "color: #FF0000; border: none; font-size: 24px; font-weight: bold;"
        )
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_close)

        top_line = QFrame(self)
        top_line.setGeometry(0, self.TITLE_H, self.W, self.LINE_H)
        top_line.setStyleSheet("background-color: #FFFFFF;")

        col_w = self.W // 3 
        video_w = self.W - col_w

        self._build_header(col_w)

        info_frame = QFrame(self)
        info_frame.setGeometry(0, self.HEADER_H + self.Y_OFFSET, col_w, self.BODY_H)
        self._build_left_info_panel(info_frame, col_w)

        video_frame = QFrame(self)
        video_frame.setGeometry(col_w, self.HEADER_H + self.Y_OFFSET, video_w, self.BODY_H)
        video_frame.setStyleSheet("background-color: #2b2b2b;")
        self._build_video_area(video_frame, video_w, self.BODY_H)

        self._draw_grid(col_w)

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

    def _build_header(self, col_w):
        menu_frame = QFrame(self)
        menu_frame.setGeometry(0, self.Y_OFFSET, col_w, self.HEADER_H)
        
        lbl_menu = QLabel("Меню управления", menu_frame)
        lbl_menu.setGeometry(0, 15, col_w, 30)
        
        btn_w = (col_w - 16) // 3
        b_style = (
            "color: white; border-radius: 18px; "
            "font-family: 'Times New Roman'; font-size: 14px; font-weight: bold;"
        )

        btn_instr = QPushButton("Инструкция", menu_frame)
        btn_instr.setGeometry(0, 65, btn_w, 36)
        btn_instr.setStyleSheet(
            f"QPushButton {{ background-color: #8D3C7F; {b_style} }} "
            f"QPushButton:hover {{ background-color: #9E4576; }}"
        )
        btn_instr.clicked.connect(self._go_instruction)

        btn_analysis = QPushButton("Анализ", menu_frame)
        btn_analysis.setGeometry(btn_w + 8, 65, btn_w, 36)
        btn_analysis.setStyleSheet(
            f"QPushButton {{ background-color: #8D3C7F; {b_style} }} "
            f"QPushButton:hover {{ background-color: #9E4576; }}"
        )
        btn_analysis.clicked.connect(self._go_analysis)

        btn_control = QPushButton("Управление", menu_frame)
        btn_control.setGeometry((btn_w + 8) * 2, 65, col_w - (btn_w + 8) * 2, 36)
        btn_control.setStyleSheet(f"QPushButton {{ background-color: #44CC29; {b_style} }}")

        logo_frame = QFrame(self)
        logo_frame.setGeometry(col_w, self.Y_OFFSET, col_w, self.HEADER_H)
        logo_frame.setStyleSheet("background: #44CC29;")
        
        lbl_logo = QLabel("НейроБодр", logo_frame)
        lbl_logo.setGeometry(0, 10, col_w, 50)
        
        logo_line = QFrame(logo_frame)
        logo_line.setGeometry(int(col_w * 0.2), 60, int(col_w * 0.6), 2)
        logo_line.setStyleSheet("background-color: white;")
        
        lbl_desc = QLabel("Программа для мониторинга\nсостояния водителей", logo_frame)
        lbl_desc.setGeometry(0, 65, col_w, 50)

        id_frame = QFrame(self)
        id_frame.setGeometry(col_w * 2, self.Y_OFFSET, self.W - col_w * 2, self.HEADER_H)
        
        lbl_id = QLabel("Идентификация", id_frame)
        lbl_id.setGeometry(0, 5, self.W - col_w * 2, 35)
        
        id_sep = QFrame(id_frame)
        id_sep.setGeometry(0, 45, self.W - col_w * 2, self.GRID_T)
        id_sep.setStyleSheet("background-color: white;")
        
        lbl_op_title = QLabel("Оператор\nопределен:", id_frame)
        lbl_op_title.setGeometry(20, 55, 110, 60)
        
        f_name = self.operator_row.get('first_name', '')
        l_name = self.operator_row.get('last_name', '')
        self.lbl_op_name = QLabel(f"{l_name} {f_name}", id_frame)
        self.lbl_op_name.setGeometry(150, 55, self.W - col_w * 2 - 160, 60)

        for w in [menu_frame, logo_frame, id_frame]:
            for lbl in w.findChildren(QLabel):
                if lbl.text() == "Меню управления":
                    lbl.setFont(QFont("Times New Roman", 18))
                elif lbl.text() == "НейроБодр":
                    lbl.setFont(QFont("Times New Roman", 20))
                elif lbl.text() == "Идентификация":
                    lbl.setFont(QFont("Times New Roman", 14))
                elif "Программа" in lbl.text():
                    lbl.setFont(QFont("Times New Roman", 14))
                elif lbl.text() == "Оператор\nопределен:":
                    lbl.setFont(QFont("Times New Roman", 14))
                else:
                    lbl.setFont(QFont("Times New Roman", 16))
                
                if w == logo_frame:
                    lbl.setStyleSheet("color: white;")
                
                if lbl.text() != "Оператор\nопределен:" and lbl != self.lbl_op_name:
                    lbl.setAlignment(Qt.AlignCenter)
                else:
                    lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

    def _build_left_info_panel(self, parent, w):
        font_label = QFont("Times New Roman", 12)
        font_val = QFont("Times New Roman", 12, QFont.Bold)
        font_header = QFont("Times New Roman", 14)
        font_term = QFont("Consolas", 10)

        y = 10
        
        dt_str = utils._now_date_str() + " / " + utils._now_time_str()
        start_str = self.operator_row.get("software_start_time", utils._now_time_str())
        
        info_items = [
            ("Дата/время:", dt_str, "lbl_dt_val"),
            ("Время запуска:", start_str, "lbl_start_val"),
            ("Состояние оператора:", "НОРМА", "lbl_state_val")
        ]

        for title, val, attr in info_items:
            lbl_t = QLabel(title, parent)
            w_label = 160 if "Состояние" in title else 120
            lbl_t.setGeometry(15, y, w_label, 22)
            lbl_t.setFont(font_label)
            
            lbl_v = QLabel(val, parent)
            x_val = 180 if "Состояние" in title else 140
            lbl_v.setGeometry(x_val, y, w - x_val, 22)
            lbl_v.setFont(font_val)
            
            if "Состояние" in title:
                lbl_v.setStyleSheet("color: #009900;")
            
            setattr(self, attr, lbl_v)
            y += 27

        for head in ["Терминальный блок", "Допустимое время"]:
            sep1 = QFrame(parent)
            sep1.setGeometry(0, y, w, 4)
            sep1.setStyleSheet("background-color: white;")
            
            lbl_h = QLabel(head, parent)
            lbl_h.setGeometry(0, y + 4, w, 30)
            lbl_h.setAlignment(Qt.AlignCenter)
            lbl_h.setFont(font_header)
            
            sep2 = QFrame(parent)
            sep2.setGeometry(0, y + 34, w, 4)
            sep2.setStyleSheet("background-color: white;")
            y += 41

            if head == "Терминальный блок":
                term_box = QFrame(parent)
                term_box.setGeometry(3, y, w - 6, 100)
                term_box.setStyleSheet("background-color: black;")
                
                self.lbl_term_text = QLabel("Состояние нормальное\nПульс --", term_box)
                self.lbl_term_text.setGeometry(5, 5, w - 20, 90)
                self.lbl_term_text.setStyleSheet("color: white; background: transparent;")
                self.lbl_term_text.setFont(font_term)
                self.lbl_term_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
                y += 103
            else:
                self.lbl_clock = QLabel("09:00", parent)
                self.lbl_clock.setGeometry(0, y + 5, w, 55) 
                self.lbl_clock.setAlignment(Qt.AlignCenter)
                self.lbl_clock.setFont(QFont("Times New Roman", 42, QFont.Bold))

    def _build_video_area(self, parent, w, h):
        self.video_label = QLabel(parent)
        self.video_label.setGeometry(0, 0, w, h)
        self.video_label.setStyleSheet("background-color: black;")

        self.video_cap = cv2.VideoCapture("videoBG.mp4")
        self.timer_video = QTimer(self)
        self.timer_video.timeout.connect(self._update_video_frame)
        self.timer_video.start(33)

        top_strip = QFrame(self.video_label)
        top_strip.setGeometry(0, 0, w, 70)
        top_strip.setStyleSheet("background-color: rgba(255, 255, 255, 150); border: none;")

        self.lbl_sq_green = ShapeWidget("circle", "#7CE4D5", top_strip)
        self.lbl_sq_green.move(10, 15)
        
        self.lbl_sq_yellow = ShapeWidget("triangle", "#F9D849", top_strip)
        self.lbl_sq_yellow.move(60, 15)
        
        self.lbl_sq_red = ShapeWidget("square", "#D0021B", top_strip)
        self.lbl_sq_red.move(110, 15)

        lbl_pulse = QLabel("Пульс:", top_strip)
        lbl_pulse.setGeometry(210, 0, 150, 70)
        lbl_pulse.setFont(QFont("Times New Roman", 28, QFont.Bold))
        lbl_pulse.setStyleSheet("color: black; background: transparent;")

        self.lbl_pulse_overlay = QLabel("--", top_strip)
        self.lbl_pulse_overlay.setGeometry(370, 0, 100, 70)
        self.lbl_pulse_overlay.setFont(QFont("Times New Roman", 42, QFont.Bold))
        self.lbl_pulse_overlay.setStyleSheet("color: #009900; background: transparent;")

        face_frame = QFrame(self.video_label)
        face_frame.setGeometry(w - 190, 0, 190, 190)
        face_frame.setStyleSheet("background-color: white;")
        
        self.lbl_cam_feed = QLabel(face_frame)
        self.lbl_cam_feed.setGeometry(2, 2, 186, 186)

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

    def _draw_grid(self, col_w):
        sep1 = QFrame(self)
        sep1.setGeometry(0, self.HEADER_H + self.Y_OFFSET, self.W, self.GRID_T)
        sep1.setStyleSheet("background-color: white;")
        
        sep2 = QFrame(self)
        sep2.setGeometry(col_w - 2, self.Y_OFFSET, self.GRID_T, self.H - self.Y_OFFSET)
        sep2.setStyleSheet("background-color: white;")
        
        sep3 = QFrame(self)
        sep3.setGeometry(col_w * 2 - 2, self.Y_OFFSET, self.GRID_T, self.HEADER_H)
        sep3.setStyleSheet("background-color: white;")
        
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
            msg = (f"Состояние оператора выходит за пределы «ВНИМАНИЕ»\n"
                   f"Пульс {p_str}\nЗапуск звукового оповещения «ВНИМАНИЕ»")
            self.lbl_term_text.setText(msg)
        else:
            msg = f"Состояние критичное!\nПульс {p_str}\nЗапуск звукового оповещения!"
            self.lbl_term_text.setText(msg)

    def _update_ui_state(self):
        self.player_warning.stop()
        self.player_alarm.stop()
        
        states = {
            "NORMAL": ("НОРМА", "#009900", "#7CE4D5", "#D0CECF", "#D0CECF", None),
            "WARNING": ("ВНИМАНИЕ", "#FFD700", "#D0CECF", "#F9D849", "#D0CECF", self.player_warning),
            "CRITICAL": ("КРИТИЧНО!", "#FF0000", "#D0CECF", "#D0CECF", "#D0021B", self.player_alarm)
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