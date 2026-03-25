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
    QWidget, QLabel, QPushButton, QFrame, QMessageBox
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
            points = [QPoint(self.width() // 2, 0), QPoint(0, self.height()), QPoint(self.width(), self.height())]
            painter.drawPolygon(QPolygon(points))
        elif self.shape_type == "square":
            painter.drawRect(0, 0, self.width(), self.height())


class ControlForm(QWidget):
    def __init__(self, operator_row: dict = None):
        super().__init__()
        
        self.operator_row = operator_row if operator_row else {}
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.csv_path = utils._csv_path(self.base_dir)

        self.pulse_norm_min = 60
        self.pulse_norm_max = 80
        self.pulse_crit_threshold = 100
        
        self._load_settings_from_csv()

        self.analysis_form = None
        self.instr_form = None

        self.W = 1000
        self.H = 450
        self.HEADER_H = 120
        self.BODY_H = self.H - self.HEADER_H
        self.GRID_T = 4

        self.fps_estimate = 30 
        self.eyes_closed_start_time = None
        self.head_tilted_start_time = None

        self.setFixedSize(self.W, self.H)
        self.setWindowTitle("НейроБодр - Мониторинг")
        self.setStyleSheet("background-color: #D9D9D9;")

        self.current_pulse_val = 0
        self.current_state = "NORMAL"
        self.start_app_time = datetime.datetime.now()
        self.remaining_seconds = 9 * 3600

        self.consecutive_frames_closed = 0
        self.fps_estimate = 30 
        
        self.player_warning = QMediaPlayer()
        self.player_alarm = QMediaPlayer()
        
        warn_path = os.path.join(self.base_dir, "yellowSound.mp3")
        alarm_path = os.path.join(self.base_dir, "redSound.mp3")
        
        if os.path.exists(warn_path):
            self.playlist_warn = QMediaPlaylist()
            self.playlist_warn.addMedia(QMediaContent(QUrl.fromLocalFile(warn_path)))
            self.playlist_warn.setPlaybackMode(QMediaPlaylist.Loop)
            self.player_warning.setPlaylist(self.playlist_warn)

        if os.path.exists(alarm_path):
            self.playlist_alarm = QMediaPlaylist()
            self.playlist_alarm.addMedia(QMediaContent(QUrl.fromLocalFile(alarm_path)))
            self.playlist_alarm.setPlaybackMode(QMediaPlaylist.Loop)
            self.player_alarm.setPlaylist(self.playlist_alarm)

        self.video_cap = None
        self.current_frame = None

        self._build_ui()
        self._init_logic()

        self.show()

    def _load_settings_from_csv(self):
        target_id = str(self.operator_row.get("id", ""))
        if not target_id or not os.path.exists(self.csv_path):
            return

        try:
            with open(self.csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("id") == target_id:
                        p_norm = row.get("pulse_normal", "")
                        if "-" in p_norm:
                            try:
                                parts = p_norm.split("-")
                                self.pulse_norm_min = int(parts[0])
                                self.pulse_norm_max = int(parts[1])
                            except: pass
                        elif p_norm.isdigit():
                            self.pulse_norm_max = int(p_norm)
                        
                        p_crit = row.get("pulse_threshold_critical", "")
                        if p_crit.isdigit():
                            self.pulse_crit_threshold = int(p_crit)
                        break
        except Exception as e:
            print(f"Ошибка чтения настроек пульса: {e}")

    def _build_ui(self):
        col_one_w = self.W // 3 
        video_w = self.W - col_one_w

        self._build_header(col_one_w)

        info_frame = QFrame(self)
        info_frame.setGeometry(0, self.HEADER_H, col_one_w, self.BODY_H)
        self._build_left_info_panel(info_frame, col_one_w)

        video_frame = QFrame(self)
        video_frame.setGeometry(col_one_w, self.HEADER_H, video_w, self.BODY_H)
        video_frame.setStyleSheet("background-color: #2b2b2b;")
        self._build_video_area(video_frame, video_w, self.BODY_H)

        self._draw_grid(col_one_w)

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
        
        cascade_path_face = os.path.join(self.base_dir, 'haarcascade_frontalface_default.xml')
        cascade_path_eye = os.path.join(self.base_dir, 'haarcascade_eye.xml')
        
        if not os.path.exists(cascade_path_face):
            cascade_path_face = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        if not os.path.exists(cascade_path_eye):
            cascade_path_eye = cv2.data.haarcascades + 'haarcascade_eye.xml'

        self.face_cascade = cv2.CascadeClassifier(cascade_path_face)
        self.eye_cascade = cv2.CascadeClassifier(cascade_path_eye)
        
        self.timer_cam = QTimer(self)
        self.timer_cam.timeout.connect(self._process_camera_frame)
        self.timer_cam.start(30)

        self._update_time_ui()


    def _build_header(self, col_one_w):
        menu_frame = QFrame(self)
        menu_frame.setGeometry(0, 0, col_one_w, self.HEADER_H)
        
        lbl_menu = QLabel("Меню управления", menu_frame)
        lbl_menu.setGeometry(0, 15, col_one_w, 30)
        lbl_menu.setAlignment(Qt.AlignCenter)
        lbl_menu.setFont(QFont("Times New Roman", 18))

        spacing = 8
        btn_h = 36
        btn_y = 65
        total_btn_w = col_one_w - (spacing * 2)
        btn_w = total_btn_w // 3
        
        base_style = "color: white; border: none; border-radius: 18px; font-family: 'Times New Roman'; font-size: 14px; font-weight: bold;"
        green_style = f"QPushButton {{ background-color: #44CC29; {base_style} }} QPushButton:hover {{ background-color: #45D44A; }}"
        purple_style = f"QPushButton {{ background-color: #8D3C7F; {base_style} }} QPushButton:hover {{ background-color: #9E4576; }}"

        self.btn_instr = QPushButton("Инструкция", menu_frame)
        self.btn_instr.setGeometry(0, btn_y, btn_w, btn_h)
        self.btn_instr.setStyleSheet(purple_style)
        self.btn_instr.clicked.connect(self._go_instruction)

        self.btn_analysis = QPushButton("Анализ", menu_frame)
        self.btn_analysis.setGeometry(btn_w + spacing, btn_y, btn_w, btn_h)
        self.btn_analysis.setStyleSheet(purple_style)
        self.btn_analysis.clicked.connect(self._go_analysis)

        self.btn_control = QPushButton("Управление", menu_frame)
        self.btn_control.setGeometry((btn_w + spacing) * 2, btn_y, col_one_w - (btn_w + spacing) * 2, btn_h)
        self.btn_control.setStyleSheet(green_style)

        logo_frame = QFrame(self)
        logo_frame.setGeometry(col_one_w, 0, col_one_w, self.HEADER_H)
        logo_frame.setStyleSheet("background: #44CC29; border: none;")
        
        lbl_logo = QLabel("НейроБодр", logo_frame)
        lbl_logo.setGeometry(0, 10, col_one_w, 50)
        lbl_logo.setAlignment(Qt.AlignCenter)
        lbl_logo.setStyleSheet("color: white; font-family: 'Times New Roman'; font-size: 20pt;")
        
        line = QFrame(logo_frame)
        line.setGeometry(int(col_one_w * 0.2), 60, int(col_one_w * 0.6), 2)
        line.setStyleSheet("background-color: white;")

        lbl_desc = QLabel("Программа для мониторинга\nсостояния водителей", logo_frame)
        lbl_desc.setGeometry(0, 65, col_one_w, 50)
        lbl_desc.setAlignment(Qt.AlignCenter)
        lbl_desc.setStyleSheet("color: white; font-family: 'Times New Roman'; font-size: 14pt;")

        real_col3_w = self.W - (col_one_w * 2)
        id_frame = QFrame(self)
        id_frame.setGeometry(col_one_w * 2, 0, real_col3_w, self.HEADER_H)
        
        lbl_id_title = QLabel("Идентификация", id_frame)
        lbl_id_title.setGeometry(0, 5, real_col3_w, 35)
        lbl_id_title.setAlignment(Qt.AlignCenter)
        lbl_id_title.setFont(QFont("Times New Roman", 14))

        id_sep = QFrame(id_frame)
        id_sep.setGeometry(0, 45, real_col3_w, self.GRID_T)
        id_sep.setStyleSheet("background-color: white;")

        lbl_op_status = QLabel("Оператор\nопределен:", id_frame)
        lbl_op_status.setGeometry(20, 55, 110, 60)
        lbl_op_status.setFont(QFont("Times New Roman", 14))
        
        self.lbl_op_name = QLabel("", id_frame)
        self.lbl_op_name.setGeometry(150, 55, real_col3_w - 160, 60)
        self.lbl_op_name.setFont(QFont("Times New Roman", 16))
        
        f_name = self.operator_row.get("first_name", "")
        l_name = self.operator_row.get("last_name", "")
        self.lbl_op_name.setText(f"{l_name} {f_name}")

    def _build_left_info_panel(self, parent, w):
        padding_left = 15
        line_th = 4           
        
        font_label = QFont("Times New Roman", 12) 
        font_val = QFont("Times New Roman", 12, QFont.Bold)
        font_header = QFont("Times New Roman", 14)
        font_term = QFont("Consolas", 10)

        y_cursor = 10
        row_h = 22            

        lbl_dt_title = QLabel("Дата/время:", parent)
        lbl_dt_title.setGeometry(padding_left, y_cursor, 120, row_h)
        lbl_dt_title.setFont(font_label)
        
        self.lbl_dt_val = QLabel(utils._now_date_str() + " / " + utils._now_time_str(), parent)
        self.lbl_dt_val.setGeometry(padding_left + 125, y_cursor, w - 130, row_h)
        self.lbl_dt_val.setFont(font_val)
        
        y_cursor += row_h + 5
        
        lbl_start_title = QLabel("Время запуска:", parent)
        lbl_start_title.setGeometry(padding_left, y_cursor, 120, row_h)
        lbl_start_title.setFont(font_label)
        
        start_t = self.operator_row.get("software_start_time", utils._now_time_str())
        self.lbl_start_val = QLabel(start_t, parent)
        self.lbl_start_val.setGeometry(padding_left + 125, y_cursor, w - 130, row_h)
        self.lbl_start_val.setFont(font_val)

        y_cursor += row_h + 5

        lbl_state_title = QLabel("Состояние оператора:", parent)
        lbl_state_title.setGeometry(padding_left, y_cursor, 160, row_h)
        lbl_state_title.setFont(font_label)
        
        self.lbl_state_val = QLabel("НОРМА", parent)
        self.lbl_state_val.setGeometry(padding_left + 165, y_cursor, w - 180, row_h)
        self.lbl_state_val.setFont(font_val)
        self.lbl_state_val.setStyleSheet("color: #009900;") 

        y_cursor += row_h + 2 

        sep1 = QFrame(parent)
        sep1.setGeometry(0, y_cursor, w, line_th)
        sep1.setStyleSheet("background-color: white;")
        y_cursor += line_th

        lbl_term_head = QLabel("Терминальный блок", parent)
        lbl_term_head.setGeometry(0, y_cursor, w, 30)
        lbl_term_head.setAlignment(Qt.AlignCenter)
        lbl_term_head.setFont(font_header)
        y_cursor += 30

        sep2 = QFrame(parent)
        sep2.setGeometry(0, y_cursor, w, line_th)
        sep2.setStyleSheet("background-color: white;")
        y_cursor += line_th + 3 

        term_h = 100
        term_box = QFrame(parent)
        term_box.setGeometry(3, y_cursor, w - 6, term_h) 
        term_box.setStyleSheet("background-color: black;")
        
        self.lbl_term_text = QLabel("Состояние нормальное\nПульс --", term_box)
        self.lbl_term_text.setGeometry(5, 5, w - 20, term_h - 10)
        self.lbl_term_text.setStyleSheet("color: white; background: transparent;")
        self.lbl_term_text.setFont(font_term)
        self.lbl_term_text.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.lbl_term_text.setWordWrap(True)
        
        y_cursor += term_h + 3

        sep3 = QFrame(parent)
        sep3.setGeometry(0, y_cursor, w, line_th)
        sep3.setStyleSheet("background-color: white;")
        y_cursor += line_th

        lbl_time_head = QLabel("Допустимое время", parent)
        lbl_time_head.setGeometry(0, y_cursor, w, 30)
        lbl_time_head.setAlignment(Qt.AlignCenter)
        lbl_time_head.setFont(font_header)
        y_cursor += 30

        sep4 = QFrame(parent)
        sep4.setGeometry(0, y_cursor, w, line_th)
        sep4.setStyleSheet("background-color: white;")
        y_cursor += line_th + 5 

        clock_h = 55 
        self.lbl_clock = QLabel("09:00", parent)
        self.lbl_clock.setGeometry(0, y_cursor, w, clock_h) 
        self.lbl_clock.setAlignment(Qt.AlignCenter)
        self.lbl_clock.setFont(QFont("Times New Roman", 42, QFont.Bold))
        self.lbl_clock.setStyleSheet("color: black;")

    def _build_video_area(self, parent, w, h):
        self.video_label = QLabel(parent)
        self.video_label.setGeometry(0, 0, w, h)
        self.video_label.setStyleSheet("background-color: black;")
        self.video_label.setAlignment(Qt.AlignCenter)

        video_filename = "videoBG.mp4"
        video_path = os.path.join(self.base_dir, video_filename)

        if os.path.exists(video_path):
            self.video_cap = cv2.VideoCapture(video_path)
            if not self.video_cap.isOpened():
                print(f"Не удалось открыть видео: {video_path}")
                self.video_cap = None
        else:
            print(f"Файл видео не найден: {video_path}")
            self.video_cap = None

        self.timer_video = QTimer(self)
        self.timer_video.timeout.connect(self._update_video_frame)
        self.timer_video.start(33)

        self.top_strip = QFrame(self.video_label)
        self.top_strip.setGeometry(0, 0, w, 70)
        self.top_strip.setStyleSheet("background-color: rgba(255, 255, 255, 150); border: none;")

        self._draw_shapes(self.top_strip)

        lbl_pulse_text = QLabel("Пульс:", self.top_strip)
        lbl_pulse_text.setGeometry(210, 0, 150, 70)
        lbl_pulse_text.setFont(QFont("Times New Roman", 28, QFont.Bold))
        lbl_pulse_text.setStyleSheet("color: black; background: transparent;")
        lbl_pulse_text.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        self.lbl_pulse_overlay = QLabel("--", self.top_strip)
        self.lbl_pulse_overlay.setGeometry(370, 0, 100, 70)
        self.lbl_pulse_overlay.setFont(QFont("Times New Roman", 42, QFont.Bold))
        self.lbl_pulse_overlay.setStyleSheet("color: #009900; background: transparent;")
        self.lbl_pulse_overlay.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)

        face_size = 190
        self.face_frame = QFrame(self.video_label)
        self.face_frame.setGeometry(w - face_size, 0, face_size, face_size)
        self.face_frame.setStyleSheet("background-color: white; border: none")

        self.lbl_cam_feed = QLabel(self.face_frame)
        self.lbl_cam_feed.setGeometry(2, 2, face_size - 4, face_size - 4)
        self.lbl_cam_feed.setScaledContents(False)

        self.top_strip.raise_()
        self.face_frame.raise_()

    def _update_video_frame(self):
        if self.video_cap is None:
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
        qimg = QImage(frame_rgb.data, w, h, bytes_per_line, QImage.Format_RGB888)

        pixmap = QPixmap.fromImage(qimg)
        scaled_pixmap = pixmap.scaled(
            self.video_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.video_label.setPixmap(scaled_pixmap)

    def _draw_shapes(self, parent):
        shape_s = 40
        y_pos = 15
        gap = 10

        self.lbl_sq_green = ShapeWidget("circle", "#7CE4D5", parent)
        self.lbl_sq_green.move(10, y_pos)

        self.lbl_sq_yellow = ShapeWidget("triangle", "#F9D849", parent)
        self.lbl_sq_yellow.move(10 + shape_s + gap, y_pos)

        self.lbl_sq_red = ShapeWidget("square", "#D0021B", parent)
        self.lbl_sq_red.move(10 + (shape_s + gap) * 2, y_pos)

    def _draw_grid(self, col_w):
        sep_h = QFrame(self)
        sep_h.setGeometry(0, self.HEADER_H, self.W, self.GRID_T)
        sep_h.setStyleSheet("background-color: white;")

        sep_v1 = QFrame(self)
        sep_v1.setGeometry(col_w - self.GRID_T//2, 0, self.GRID_T, self.H)
        sep_v1.setStyleSheet("background-color: white;")

        sep_v2 = QFrame(self)
        sep_v2.setGeometry(col_w * 2 - self.GRID_T//2, 0, self.GRID_T, self.HEADER_H)
        sep_v2.setStyleSheet("background-color: white;")


    @pyqtSlot(str, str, str)
    def _on_pulse_data(self, status_conn, status_pulse, pulse_str):
        if pulse_str.isdigit():
            self.current_pulse_val = int(pulse_str)
            self.lbl_pulse_overlay.setText(pulse_str)
        else:
            self.current_pulse_val = 0
            self.lbl_pulse_overlay.setText("--")
        
        self._check_status()

    def _process_camera_frame(self):
        ret, frame = self.cap.read()
        if not ret: return

        frame = cv2.flip(frame, 1)
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
        
        detected_eyes = False
        detected_face = False

        if len(faces) > 0:
            detected_face = True
            (x, y, w, h) = sorted(faces, key=lambda f: f[2]*f[3], reverse=True)[0]
            cv2.rectangle(frame, (x, y), (x+w, y+h), (0, 255, 0), 2)
            roi_gray = gray[y:y+h, x:x+w]
            roi_color = frame[y:y+h, x:x+w]
            eyes = self.eye_cascade.detectMultiScale(roi_gray, 1.1, 10, minSize=(20, 20))
            if len(eyes) > 0:
                detected_eyes = True
                for (ex, ey, ew, eh) in eyes:
                    cv2.rectangle(roi_color, (ex, ey), (ex+ew, ey+eh), (255, 0, 0), 2)

        current_time = time.time()

        if detected_face and not detected_eyes:
            if self.eyes_closed_start_time is None:
                self.eyes_closed_start_time = current_time
        else:
            if not detected_face:
                if self.eyes_closed_start_time is None:
                    self.eyes_closed_start_time = current_time
            else:
                self.eyes_closed_start_time = None

        if not detected_face:
            if self.head_tilted_start_time is None:
                self.head_tilted_start_time = current_time
        else:
            self.head_tilted_start_time = None

        utils._draw_to_label_with_dpr(frame, self.lbl_cam_feed)
        self._check_status()

    def _check_status(self):
        current_time = time.time()
        
        seconds_closed = (current_time - self.eyes_closed_start_time) if self.eyes_closed_start_time else 0
        seconds_tilted = (current_time - self.head_tilted_start_time) if self.head_tilted_start_time else 0
        
        p = self.current_pulse_val
        norm_min = self.pulse_norm_min
        norm_max = self.pulse_norm_max
        crit = self.pulse_crit_threshold

        is_pulse_red = (p > 0 and (p <= norm_min * 0.7 or p >= crit))
        is_eyes_red = (seconds_closed > 7.0 or seconds_tilted > 7.0)

        is_pulse_yellow = (p > 0 and (p <= norm_min * 0.8 or (p >= norm_max * 1.2 and p < crit)))
        is_eyes_yellow = (seconds_closed > 4.0)
        is_head_yellow = (seconds_tilted > 4.0)

        new_state = "NORMAL"
        if is_pulse_red or is_eyes_red:
            new_state = "CRITICAL"
        elif is_pulse_yellow or is_eyes_yellow or is_head_yellow:
            new_state = "WARNING"

        if new_state != self.current_state:
            self.current_state = new_state
            self._update_ui_state()
            self._update_csv_log()
        
        self._update_terminal_text()

    def _update_terminal_text(self):
        p_str = str(self.current_pulse_val) if self.current_pulse_val > 0 else "--"
        term_txt = ""

        if self.current_state == "NORMAL":
            term_txt = f"Состояние нормальное\nПульс {p_str}"
        elif self.current_state == "WARNING":
            term_txt = f"Состояние оператора выходит за пределы «ВНИМАНИЕ»\nПульс {p_str}\nЗапуск звукового оповещения «ВНИМАНИЕ»"
        elif self.current_state == "CRITICAL":
            term_txt = f"Состояние критичное!\nПульс {p_str}\nЗапуск звукового оповещения!"
        
        self.lbl_term_text.setText(term_txt)

    def _update_ui_state(self):
        common_border = "border: 2px solid #0000FF;"
        
        st_green_on = f"background-color: #07D40B; {common_border}"
        st_yellow_on = f"background-color: #FFFC00; {common_border}"
        st_red_on = f"background-color: #D0021B; {common_border}"

        st_green_off = f"background-color: #D0CECF; {common_border}"
        st_yellow_off = f"background-color: #D0CECF; {common_border}"
        st_red_off = f"background-color: #D0CECF; {common_border}"

        self.player_warning.stop()
        self.player_alarm.stop()
        
        off_color = "#D0CECF"

        if self.current_state == "NORMAL":
            self.lbl_state_val.setText("НОРМА")
            self.lbl_state_val.setStyleSheet("color: #009900;")
            self.lbl_pulse_overlay.setStyleSheet("color: #009900; background: transparent;")
            
            self.lbl_sq_green.set_color("#7CE4D5")
            self.lbl_sq_yellow.set_color(off_color)
            self.lbl_sq_red.set_color(off_color)

        elif self.current_state == "WARNING":
            self.lbl_state_val.setText("ВНИМАНИЕ")
            self.lbl_state_val.setStyleSheet("color: #FFD700;")
            self.lbl_pulse_overlay.setStyleSheet("color: #FFD700; background: transparent;")
            
            self.lbl_sq_green.set_color(off_color)
            self.lbl_sq_yellow.set_color("#F9D849")
            self.lbl_sq_red.set_color(off_color)
            
            self.player_warning.play()

        elif self.current_state == "CRITICAL":
            self.lbl_state_val.setText("КРИТИЧНО!")
            self.lbl_state_val.setStyleSheet("color: #FF0000;")
            self.lbl_pulse_overlay.setStyleSheet("color: #FF0000; background: transparent;")
            
            self.lbl_sq_green.set_color(off_color)
            self.lbl_sq_yellow.set_color(off_color)
            self.lbl_sq_red.set_color("#D0021B")

            self.player_alarm.play()

    def _update_time_logic(self):
        self.lbl_dt_val.setText(utils._now_date_str() + " / " + utils._now_time_str())

        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            hours = self.remaining_seconds // 3600
            minutes = (self.remaining_seconds % 3600) // 60
            seconds = self.remaining_seconds % 60
            time_str = f"{hours:02d}:{minutes:02d}"
            self.lbl_clock.setText(time_str)
        else:
            self.timer_main.stop()
            self.lbl_clock.setText("00:00")
            QMessageBox.information(self, "Конец", "Время вышло!")

        self._update_csv_log()

    def _update_time_ui(self):
        self.lbl_dt_val.setText(utils._now_date_str() + " / " + utils._now_time_str())

    def _update_csv_log(self):
        target_id = str(self.operator_row.get("id", ""))
        if not target_id or not os.path.exists(self.csv_path):
            return

        updates = {
            "current_pulse": str(self.current_pulse_val),
            "operator_status": self.current_state,
            "drive_duration": utils._seconds_to_hms((datetime.datetime.now() - self.start_app_time).total_seconds()),
        }

        all_rows = []
        fieldnames = []

        try:
            with open(self.csv_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                fieldnames = list(reader.fieldnames) if reader.fieldnames else []
                all_rows = list(reader)

            for key in updates.keys():
                if key not in fieldnames:
                    fieldnames.append(key)

            updated_any = False
            for row in all_rows:
                if row.get("id") == target_id:
                    for key, val in updates.items():
                        row[key] = val
                    updated_any = True
                    break
            
            if updated_any:
                with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_rows)

        except Exception as e:
            print(f"Ошибка обновления CSV: {e}")

    def _go_instruction(self):
        from instruction_form import InstructionForm
        if not self.instr_form:
            self.instr_form = InstructionForm(self.operator_row)
        self.instr_form.show()
        self.close()

    def _go_analysis(self):
        from analysis_form import AnalysisForm
        if not self.analysis_form:
            self.analysis_form = AnalysisForm(self.operator_row)
        self.analysis_form.show()
        self.close()

    def closeEvent(self, event):
        self._update_csv_log()

        self.worker_pulse.stop()
        self.thread_pulse.quit()
        self.thread_pulse.wait()

        self.timer_main.stop()
        self.timer_cam.stop()
        self.timer_video.stop()

        if self.cap.isOpened():
            self.cap.release()

        if self.video_cap is not None:
            self.video_cap.release()

        self.player_warning.stop()
        self.player_alarm.stop()

        super().closeEvent(event)