import sys
import os
import csv
import datetime
import utils
from PyQt5.QtCore import QPoint, Qt, QRegularExpression, QTimer, QUrl, QSize
from PyQt5.QtGui import (
    QBrush, QColor, QFont, QPainter, QPixmap, QGuiApplication, QPolygon, QRegularExpressionValidator, QImage
)
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QApplication, QVBoxLayout, QHBoxLayout, QLineEdit, QMessageBox
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist

class ShapeWidget(QWidget):
    def __init__(self, shape_type, color, parent=None):
        super().__init__(parent)
        self.shape_type = shape_type
        self.color = color
        self.setFixedSize(80, 80)

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


class AuthScreen(QWidget):
    def __init__(self, remote_form):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.remote_form = remote_form

        self.setFixedSize(310, 150)
        self.setWindowTitle("Авторизация")
        self.setStyleSheet("background-color: #D9D9D9;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.top_grey_area = QWidget(self)
        self.top_grey_area.setFixedHeight(24)
        self.top_grey_area.setStyleSheet("background-color: #D9D9D9; border: none;")
        
        top_layout = QHBoxLayout(self.top_grey_area)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("×", self.top_grey_area)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("color: #FF0000; background: transparent; border: none; font-size: 24px; font-weight: bold;")
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_close)
        
        main_layout.addWidget(self.top_grey_area)

        self.top_white_line = QWidget(self)
        self.top_white_line.setFixedHeight(3)
        self.top_white_line.setStyleSheet("background-color: #FFFFFF; border: none;")
        main_layout.addWidget(self.top_white_line)

        content_container = QWidget(self)
        main_layout.addWidget(content_container)

        root = QVBoxLayout(content_container)
        root.setContentsMargins(15, 15, 15, 15)
        root.setSpacing(10)

        title = QLabel("Введите ID_оператора", self)
        title.setWordWrap(True)
        title.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        title.setFont(QFont("Times New Roman", 16, QFont.Normal))
        title.setStyleSheet("color: #000000; background: transparent;")
        root.addWidget(title)

        root.addStretch(1)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(10)

        self.in_id = QLineEdit(self)
        self.in_id.setFixedHeight(36)
        self.in_id.setFont(QFont("Times New Roman", 18, QFont.Normal))
        self.in_id.setStyleSheet("""
            QLineEdit {
                background-color: #FFFFFF;
                border: none;
                padding-left: 8px;
            }
        """)
        self.in_id.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d+"), self))

        self.btn_login = QPushButton("Далее", self)
        self.btn_login.setFixedSize(100, 36)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2C; color: #FFFFFF; border: none;
                border-radius: 6px; font-family: "Times New Roman"; font-size: 13px; font-weight: 600;
            }
            QPushButton:hover { background-color: #44CC29; }
            QPushButton:pressed { background-color: #1F1F1F; }
        """)

        self.btn_login.clicked.connect(self.on_login)

        row.addWidget(self.in_id, 1)
        row.addWidget(self.btn_login, 0)
        root.addLayout(row)

    def on_login(self):
        user_id = self.in_id.text().strip()
        if not user_id:
            return

        csv_path = utils._csv_path()
        if not os.path.exists(csv_path):
            QMessageBox.critical(self, "Ошибка", f"Файл {csv_path} не найден!")
            return

        found_user = None
        try:
            with open(csv_path, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if row.get("id") == user_id:
                        found_user = row
                        break
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка чтения CSV: {e}")
            return

        if found_user:
            self.remote_form.init_session(found_user)
            self.remote_form.show()
            self.close()
        else:
            QMessageBox.warning(self, "Ошибка", "Оператор с таким ID не найден")

    def position_over_terminal(self, parent):
        parent_global_pos = parent.mapToGlobal(QPoint(0, 0))
        
        col_w = parent.W // 3
        
        black_area_y_offset = parent.FRAME_H + parent.HEADER_H + parent.SECTION_H
        black_area_h = parent.BODY_H - parent.SECTION_H
        
        abs_x = parent_global_pos.x() + col_w
        abs_y = parent_global_pos.y() + black_area_y_offset
        
        center_x = abs_x + (col_w - self.width()) // 2
        center_y = abs_y + (black_area_h - self.height()) // 2
        
        self.move(center_x, center_y)


class RemoteForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self._old_pos = None
        
        self.is_movable = False

        self.W = 1000
        self.H = 450
        self.FRAME_H = 34
        self.HEADER_H = 120
        self.BODY_H = self.H - self.HEADER_H
        self.SECTION_H = 44
        self.GRID_T = 4

        self.setFixedSize(self.W, self.H + self.FRAME_H)
        self.setWindowTitle("Удаленный мониторинг")
        self.setStyleSheet("background-color: #D9D9D9;")

        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.player_warning = QMediaPlayer()
        self.player_alarm = QMediaPlayer()
        self._setup_audio()

        self.timer_monitor = QTimer(self)
        self.timer_monitor.timeout.connect(self._update_monitor_data)

        self.operator_data = {}
        self.start_time = None
        self.current_status = "NORMAL"

        self._build_ui()

        self.auth_window = None

    def mousePressEvent(self, event):
        if self.is_movable and event.button() == Qt.LeftButton and event.y() <= self.FRAME_H:
            self._old_pos = event.globalPos()

    def mouseMoveEvent(self, event):
        if self.is_movable and self._old_pos is not None:
            delta = QPoint(event.globalPos() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPos()

    def mouseReleaseEvent(self, event):
        self._old_pos = None

    def _setup_audio(self):
        warn_path = os.path.join(self.base_dir, "warning.wav")
        alarm_path = os.path.join(self.base_dir, "alarm.wav")

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

    def init_session(self, user_row):
        self.operator_data = user_row

        self.is_movable = True

        l_name = user_row.get("last_name", "")
        f_name = user_row.get("first_name", "")
        p_name = user_row.get("middle_name", "") 
        age = user_row.get("age", "")

        self.lbl_name.setText(f"{l_name} {f_name}\n{p_name}")
        self.lbl_age.setText(f"{age} лет")

        op_id = int(user_row.get("id", "0"))
        ops_dir = utils._ensure_dirs(self.base_dir)
        photo_path = os.path.join(ops_dir, f"ID_{utils._id_str(op_id)}.jpg")

        if os.path.exists(photo_path):
            pix = QPixmap(photo_path)
            scaled_pix = pix.scaled(self.photo.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.photo.setPixmap(scaled_pix)
            self.photo.setText("")
        else:
            self.photo.setPixmap(QPixmap())
            self.photo.setText("Нет фото")

        csv_start_time = user_row.get("software_start_time", "")
        if csv_start_time:
            try:
                t_parts = csv_start_time.split(":") 
                now = datetime.datetime.now()
                self.start_time = now.replace(hour=int(t_parts[0]), minute=int(t_parts[1]), second=int(t_parts[2]))
            except:
                self.start_time = datetime.datetime.now()
        else:
            self.start_time = datetime.datetime.now()

        self.lbl_start.setText(f"Время запуска ПО: <b>{self.start_time.strftime('%H:%M:%S')}</b>")

        self.timer_monitor.start(1000)

    def _update_monitor_data(self):
        current_pulse = 0
        status_from_file = ""
        drive_duration_str = "00:00:00"

        csv_path = utils._csv_path()
        target_id = self.operator_data.get("id")

        if os.path.exists(csv_path) and target_id:
            try:
                with open(csv_path, "r", newline="", encoding="utf-8") as f:
                    reader = csv.DictReader(f)
                    for row in reader:
                        if row.get("id") == target_id:
                            p_str = row.get("current_pulse", "0")
                            current_pulse = int(p_str) if p_str.isdigit() else 0
                            status_from_file = row.get("operator_status", "")
                            drive_duration_str = row.get("drive_duration", "00:00:00")
                            break
            except Exception:
                pass

        if not status_from_file:
            self.mid_info.setText("Ожидание данных...\nОператор еще не перешел в режим «Управление».")
            self.lbl_drive.setText("Время в дороге: <b>--:--:--</b>")
            self.lbl_left.setText("Оставшееся время: <b>--:--:--</b>")
            self.lbl_status.setText("Состояние: <span style='color:gray'>ОЖИДАНИЕ</span>")
            self.lbl_pulse_val.setText("--")
            
            st_off = "background-color: #D0CECF; border: 2px solid #0000FF;"
            self.lbl_sq_green.setStyleSheet(st_off)
            self.lbl_sq_yellow.setStyleSheet(st_off)
            self.lbl_sq_red.setStyleSheet(st_off)
            return

        self.current_status = status_from_file

        now = datetime.datetime.now()
        self.lbl_dt.setText(f"Дата/время: <b>{now.strftime('%d.%m.%Y')} / {now.strftime('%H:%M:%S')}</b>")

        self.lbl_drive.setText(f"Время в дороге: <b>{drive_duration_str}</b>")

        seconds_in_road = utils._parse_hms_to_seconds(drive_duration_str)
        remaining = max(0, 9 * 3600 - seconds_in_road)
        rh = remaining // 3600
        rm = (remaining % 3600) // 60
        rs = remaining % 60
        self.lbl_left.setText(f"Оставшееся время: <b>{rh:02d}:{rm:02d}:{rs:02d}</b>")

        self._update_indication_block(current_pulse)
        self._update_terminal_block(current_pulse)

    def _update_indication_block(self, pulse):
        if pulse > 0:
            self.lbl_pulse_val.setText(str(pulse))
        else:
            self.lbl_pulse_val.setText("--")

        common_border = "border: 2px solid #0000FF;"
        st_green_on = f"background-color: #07D40B; {common_border}"
        st_yellow_on = f"background-color: #FFFC00; {common_border}"
        st_red_on = f"background-color: #D0021B; {common_border}"
        st_off = "#D0CECF"

        if self.current_status == "NORMAL":
            self.player_warning.stop()
            self.player_alarm.stop()

            self.lbl_status.setText("Состояние: <span style='color:green'>НОРМА</span>")
            self.lbl_pulse_val.setStyleSheet("color: #009900; background: transparent;")

            self.lbl_sq_green.setStyleSheet(st_green_on)
            self.lbl_sq_yellow.setStyleSheet(st_off)
            self.lbl_sq_red.setStyleSheet(st_off)

            self.lbl_sq_green.set_color("#7CE4D5")
            self.lbl_sq_yellow.set_color(st_off)
            self.lbl_sq_red.set_color(st_off)

        elif self.current_status == "WARNING":
            if self.player_warning.state() != QMediaPlayer.PlayingState:
                self.player_warning.play()
            self.player_alarm.stop()

            self.lbl_status.setText("Состояние: <span style='color:#FFD700'>ВНИМАНИЕ</span>")
            self.lbl_pulse_val.setStyleSheet("color: #FFD700; background: transparent;")

            self.lbl_sq_green.setStyleSheet(st_off)
            self.lbl_sq_yellow.setStyleSheet(st_yellow_on)
            self.lbl_sq_red.setStyleSheet(st_off)

            self.lbl_sq_green.set_color(st_off)
            self.lbl_sq_yellow.set_color("#F9D849")
            self.lbl_sq_red.set_color(st_off)

        elif self.current_status == "CRITICAL":
            self.player_warning.stop()
            if self.player_alarm.state() != QMediaPlayer.PlayingState:
                self.player_alarm.play()

            self.lbl_status.setText("Состояние: <span style='color:red'>КРИТИЧНО!</span>")
            self.lbl_pulse_val.setStyleSheet("color: red; background: transparent;")

            self.lbl_sq_green.setStyleSheet(st_off)
            self.lbl_sq_yellow.setStyleSheet(st_off)
            self.lbl_sq_red.setStyleSheet(st_red_on)

            self.lbl_sq_green.set_color(st_off)
            self.lbl_sq_yellow.set_color(st_off)
            self.lbl_sq_red.set_color("#D0021B")

    def _update_terminal_block(self, pulse):
        p_str = str(pulse) if pulse > 0 else "--"
        term_txt = ""

        if self.current_status == "NORMAL":
            term_txt = f"Состояние нормальное\nПульс {p_str}"
        elif self.current_status == "WARNING":
            term_txt = f"Состояние оператора выходит за пределы «ВНИМАНИЕ»\nПульс {p_str}\nЗапуск звукового оповещения «ВНИМАНИЕ»"
        elif self.current_status == "CRITICAL":
            term_txt = f"Состояние критичное!\nПульс {p_str}\nЗапуск звукового оповещения!"

        self.mid_info.setText(term_txt)

    def stop_program(self):
        self.timer_monitor.stop()
        self.player_warning.stop()
        self.player_alarm.stop()

        self.lbl_sq_green.set_color("white")
        self.lbl_sq_yellow.set_color("white")
        self.lbl_sq_red.set_color("white")

        self._refresh_left_info()
        self.mid_info.setText("")
        self.lbl_pulse_val.setText("")
        self.lbl_sq_green.setStyleSheet("background-color: white; border: 2px solid #0000FF;")
        self.lbl_sq_yellow.setStyleSheet("background-color: white; border: 2px solid #0000FF;")
        self.lbl_sq_red.setStyleSheet("background-color: white; border: 2px solid #0000FF;")

        self.is_movable = False

        self.auth_window = AuthScreen(self)
        self.auth_window.position_over_terminal(self)
        self.auth_window.show()

    def _build_ui(self):
        self.top_grey_area = QWidget(self)
        self.top_grey_area.setGeometry(0, 0, self.W, 30)
        self.top_grey_area.setStyleSheet("background-color: #D9D9D9; border: none;")
        
        top_layout = QHBoxLayout(self.top_grey_area)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("×", self.top_grey_area)
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("color: #FF0000; background: transparent; border: none; font-size: 36px; font-weight: bold;")
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_close)

        self.top_white_line = QWidget(self)
        self.top_white_line.setGeometry(0, 30, self.W, 4)
        self.top_white_line.setStyleSheet("background-color: #FFFFFF; border: none;")

        header = QFrame(self)
        header.setGeometry(0, self.FRAME_H, self.W, self.HEADER_H)
        header.setStyleSheet("background-color: #44CC29; border: none;")

        t1 = QLabel("НейроБодр", header)
        t1.setGeometry(0, 6, self.W, 62)
        t1.setAlignment(Qt.AlignCenter)
        t1.setStyleSheet("color: white; background: transparent;")
        t1.setFont(QFont("Times New Roman", 40, QFont.Bold))

        line = QFrame(header)
        line.setGeometry(int(self.W * 0.16), 76, int(self.W * 0.68), 2)
        line.setStyleSheet("background-color: white; border: none;")

        t2 = QLabel("Программа для мониторинга состояния водителей", header)
        t2.setGeometry(0, 80, self.W, 30)
        t2.setAlignment(Qt.AlignCenter)
        t2.setStyleSheet("color: white; background: transparent;")
        t2.setFont(QFont("Times New Roman", 16, QFont.Normal))

        header_bottom = QFrame(self)
        header_bottom.setGeometry(0, self.FRAME_H + self.HEADER_H - self.GRID_T, self.W, self.GRID_T)
        header_bottom.setStyleSheet("background-color: #FFFFFF; border: none;")
        header_bottom.raise_()

        body = QFrame(self)
        body.setGeometry(0, self.FRAME_H + self.HEADER_H, self.W, self.BODY_H)
        body.setStyleSheet("background-color: #D9D9D9; border: none;")

        col_w = self.W // 3
        col3_w = self.W - col_w * 2

        self.left = QFrame(body)
        self.left.setGeometry(0, 0, col_w, self.BODY_H)
        self.left.setStyleSheet("background-color: #D9D9D9; border: none;")

        self.mid = QFrame(body)
        self.mid.setGeometry(col_w, 0, col_w, self.BODY_H)
        self.mid.setStyleSheet("background-color: black; border: none;")

        self.right = QFrame(body)
        self.right.setGeometry(col_w * 2, 0, col3_w, self.BODY_H)
        self.right.setStyleSheet("background-color: #D9D9D9; border: none;")

        self._section_header(self.left, "Информация оператора", col_w)
        self._section_header(self.mid, "Терминальный блок", col_w)
        self._section_header(self.right, "Блок индикации", col3_w)

        self._build_left_info(col_w)

        self.mid_info = QLabel("", self.mid)
        self.mid_info.setGeometry(20, self.SECTION_H + 20, col_w - 40, 150)
        self.mid_info.setStyleSheet("color: white; background: transparent;")
        self.mid_info.setFont(QFont("Consolas", 11, QFont.Normal))
        self.mid_info.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.mid_info.setWordWrap(True)

        self.lbl_pulse_title = QLabel("Пульс:", self.right)
        self.lbl_pulse_title.setGeometry(20, self.SECTION_H + 20, 120, 50)
        self.lbl_pulse_title.setStyleSheet("color: black; background: transparent;")
        self.lbl_pulse_title.setFont(QFont("Times New Roman", 28, QFont.Bold))

        self.lbl_pulse_val = QLabel("", self.right)
        self._draw_shapes(self.right)
        self.lbl_pulse_val.setGeometry(150, self.SECTION_H + 15, 100, 60)
        self.lbl_pulse_val.setStyleSheet("color: #D32F2F; background: transparent;")
        self.lbl_pulse_val.setFont(QFont("Times New Roman", 42, QFont.Bold))

        btn_w, btn_h = 130, 40
        self.btn_next = QPushButton("Стоп программа", self.right)
        self.btn_next.setGeometry(col3_w - btn_w - 20, self.BODY_H - btn_h - 20, btn_w, btn_h)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2C; color: #FFFFFF; border: none;
                border-radius: 6px; font-size: 14px; font-weight: 600;
            }
            QPushButton:hover { background-color: #44CC29; }
        """)
        self.btn_next.clicked.connect(self.stop_program)

        sep1 = QFrame(body)
        sep1.setGeometry(col_w - self.GRID_T // 2, 0, self.GRID_T, self.BODY_H)
        sep1.setStyleSheet("background-color: #FFFFFF; border: none;")

        sep2 = QFrame(body)
        sep2.setGeometry(col_w * 2 - self.GRID_T // 2, 0, self.GRID_T, self.BODY_H)
        sep2.setStyleSheet("background-color: #FFFFFF; border: none;")

        sep_h = QFrame(body)
        sep_h.setGeometry(0, self.SECTION_H, self.W, self.GRID_T)
        sep_h.setStyleSheet("background-color: #FFFFFF; border: none;")

        sep1.raise_()
        sep2.raise_()
        sep_h.raise_()

    def _section_header(self, parent: QWidget, text: str, width: int):
        h = QFrame(parent)
        h.setGeometry(0, 0, width, self.SECTION_H)
        h.setStyleSheet("background-color: #D9D9D9; border: none;")
        lbl = QLabel(text, h)
        lbl.setGeometry(0, 0, width, self.SECTION_H)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setStyleSheet("color: black; background: transparent;")
        lbl.setFont(QFont("Times New Roman", 14, QFont.Bold))

    def _build_left_info(self, col_w: int):
        y = self.SECTION_H + 20
        line_spacing = 30

        photo_size = 90
        self.photo = QLabel(self.left)
        self.photo.setGeometry(10, y, photo_size, 100)
        self.photo.setStyleSheet("background-color: white; border: none;")
        self.photo.setAlignment(Qt.AlignCenter)
        self.photo.setScaledContents(True)

        text_x = 18 + photo_size + 10
        self.lbl_name = QLabel(self.left)
        self.lbl_name.setGeometry(text_x, y + 5, col_w - text_x - 18, 70)
        self.lbl_name.setStyleSheet("color: black; background: transparent;")
        self.lbl_name.setFont(QFont("Times New Roman", 16, QFont.Normal))
        self.lbl_name.setWordWrap(True)

        self.lbl_age = QLabel(self.left)
        self.lbl_age.setGeometry(text_x, y + 70, col_w - text_x - 18, 28)
        self.lbl_age.setStyleSheet("color: black; background: transparent;")
        self.lbl_age.setFont(QFont("Times New Roman", 16, QFont.Normal))

        y2 = y + photo_size + 15

        self.lbl_dt = QLabel(self.left)
        self.lbl_dt.setGeometry(18, y2, col_w - 36, 26)
        self.lbl_dt.setStyleSheet("color: black; background: transparent;")
        self.lbl_dt.setFont(QFont("Times New Roman", 14))

        self.lbl_start = QLabel(self.left)
        self.lbl_start.setGeometry(18, y2 + line_spacing, col_w - 36, 26)
        self.lbl_start.setFont(QFont("Times New Roman", 14))

        self.lbl_drive = QLabel(self.left)
        self.lbl_drive.setGeometry(18, y2 + line_spacing * 2, col_w - 36, 26)
        self.lbl_drive.setFont(QFont("Times New Roman", 14))

        self.lbl_left = QLabel(self.left)
        self.lbl_left.setGeometry(18, y2 + line_spacing * 3, col_w - 36, 26)
        self.lbl_left.setFont(QFont("Times New Roman", 14))

        self.lbl_status = QLabel(self.left)
        self.lbl_status.setGeometry(18, y2 + line_spacing * 4, col_w - 36, 26)
        self.lbl_status.setFont(QFont("Times New Roman", 14))

        self._refresh_left_info()

    def _refresh_left_info(self):
        self.lbl_name.setText("Фамилия Имя Отчество")
        self.lbl_age.setText("Возраст")
        self.lbl_dt.setText("Дата/время: <b>00.00.0000 / 00:00:00</b>")
        self.lbl_start.setText("Время запуска ПО: <b>00:00:00</b>")
        self.lbl_drive.setText("Время в дороге: <b>00:00:00</b>")
        self.lbl_left.setText("Оставшееся время: <b>00:00:00</b>")
        self.lbl_status.setText("Состояние: ")

        default_img = os.path.join(self.base_dir, "assets", "user.png")
        pix = QPixmap(default_img)
        if pix.isNull():
             self.photo.setText("Нет фото")
        else:
             self.photo.setPixmap(pix.scaled(self.photo.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _draw_shapes(self, parent):
        shape_s = 80
        gap = 10
        total_width = 3 * shape_s + 2 * gap
        
        parent_rect = parent.geometry()
        center_x = parent_rect.width() // 2
        center_y = parent_rect.height() // 2 + 20
        x_start = center_x - total_width // 2
        y_start = center_y - (shape_s // 2)

        self.lbl_sq_green = ShapeWidget("circle", "white", parent)
        self.lbl_sq_green.move(x_start, y_start)

        self.lbl_sq_yellow = ShapeWidget("triangle", "white", parent)
        self.lbl_sq_yellow.move(x_start + shape_s + gap, y_start)

        self.lbl_sq_red = ShapeWidget("square", "white", parent)
        self.lbl_sq_red.move(x_start + 2 * (shape_s + gap), y_start)


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setFont(QFont("Times New Roman", 14))

    main_window = RemoteForm()
    
    screen_rect = QApplication.desktop().availableGeometry()
    x = (screen_rect.width() - main_window.width()) // 2
    y = (screen_rect.height() - main_window.height()) // 2
    main_window.move(x, y)
    
    main_window.show()

    auth_window = AuthScreen(main_window)
    auth_window.position_over_terminal(main_window)
    auth_window.show()

    sys.exit(app.exec_())