import sys
import os
import csv
import datetime

import utils
from PyQt5.QtCore import QPoint, Qt, QRegularExpression, QTimer, QUrl
from PyQt5.QtGui import (
    QBrush, QColor, QFont, QPainter, QPixmap, 
    QGuiApplication, QPolygon, QRegularExpressionValidator
)
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QApplication, 
    QVBoxLayout, QHBoxLayout, QLineEdit, QMessageBox, QSpacerItem, QSizePolicy, QGridLayout
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
            points = [
                QPoint(self.width() // 2, 0),
                QPoint(0, self.height()),
                QPoint(self.width(), self.height())
            ]
            painter.drawPolygon(QPolygon(points))
        
        elif self.shape_type == "square":
            painter.drawRect(0, 0, self.width(), self.height())

class AuthScreen(QWidget):
    def __init__(self, remote_form):
        super().__init__()
        self.remote_form = remote_form
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setWindowModality(Qt.ApplicationModal)
        self.setFixedSize(310, 150)
        self.setWindowTitle("Авторизация")
        self.setStyleSheet("background-color: #D9D9D9;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_grey = QWidget(self)
        top_grey.setFixedHeight(24)
        top_layout = QHBoxLayout(top_grey)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("X", top_grey)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "color: #FF0000; border: none; font-size: 24px; font-weight: bold;"
        )
        self.btn_close.clicked.connect(self.close)
        
        top_layout.addWidget(self.btn_close)
        main_layout.addWidget(top_grey)

        top_white = QWidget(self)
        top_white.setFixedHeight(3)
        top_white.setStyleSheet("background-color: #FFFFFF;")
        main_layout.addWidget(top_white)

        content_container = QWidget(self)
        main_layout.addWidget(content_container)

        root = QVBoxLayout(content_container)
        root.setContentsMargins(15, 15, 15, 15)

        title = QLabel("Введите ID_оператора", self)
        title.setFont(QFont("Times New Roman", 16))
        root.addWidget(title, alignment=Qt.AlignLeft | Qt.AlignTop)
        root.addStretch(1)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.in_id = QLineEdit(self)
        self.in_id.setFixedHeight(36)
        self.in_id.setFont(QFont("Times New Roman", 18))
        self.in_id.setStyleSheet(
            "background-color: #FFFFFF; border: none; padding-left: 8px;"
        )
        self.in_id.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d+"), self)
        )

        self.btn_login = QPushButton("Далее", self)
        self.btn_login.setFixedSize(100, 36)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton { 
                background-color: #2C2C2C; 
                color: #FFFFFF; 
                border-radius: 6px; 
                font-weight: 600; 
                font-size: 13px; 
            }
            QPushButton:hover { background-color: #44CC29; }
        """)
        self.btn_login.clicked.connect(self.on_login)

        row.addWidget(self.in_id, 1)
        row.addWidget(self.btn_login, 0)
        root.addLayout(row)

    def on_login(self):
        user_id = self.in_id.text().strip()
        if not user_id:
            return

        found_user = None
        try:
            with open(utils._csv_path(), "r", newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("id") == user_id:
                        found_user = row
                        break
        except Exception:
            pass

        if found_user:
            self.remote_form.init_session(found_user)
            self.remote_form.show()
            self.close()
        else:
            QMessageBox.warning(self, "Ошибка", "Оператор с таким ID не найден")

    def position_over_terminal(self, parent):
        pgp = parent.mapToGlobal(QPoint(0, 0))
        
        abs_x = pgp.x() + (parent.W // 3)
        abs_y = pgp.y() + 34 + 120 + 44 
        
        target_x = abs_x + ((parent.W // 3) - self.width()) // 2
        target_y = abs_y + (parent.BODY_H - 44 - self.height()) // 2
        
        self.move(target_x, target_y)

class RemoteForm(QWidget):
    def __init__(self):
        super().__init__()
        
        self.W, self.H = 1000, 450
        self.FRAME_H = 34
        self.HEADER_H = 120
        self.SECTION_H = 44
        self.BODY_H = self.H - self.HEADER_H

        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setFixedSize(self.W, self.H + self.FRAME_H)
        self.setWindowTitle("Удаленный мониторинг")
        self.setStyleSheet("background-color: #D9D9D9;")
        
        self._old_pos = None
        self.is_movable = False
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

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

        self.timer_monitor = QTimer(self)
        self.timer_monitor.timeout.connect(self._update_monitor_data)

        self.operator_data = {}
        self.start_time = None
        self.current_status = "NORMAL"
        self.auth_window = None

        self._build_ui()

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

    def init_session(self, user_row):
        self.operator_data = user_row
        self.is_movable = True
        
        name_text = (
            f"{user_row.get('last_name', '')} {user_row.get('first_name', '')}\n"
            f"{user_row.get('middle_name', '')}"
        )
        self.lbl_name.setText(name_text)
        self.lbl_age.setText(f"{user_row.get('age', '')} лет")

        photo_name = f"ID_{utils._id_str(int(user_row.get('id', '0')))}.jpg"
        photo_path = os.path.join(utils._ensure_dirs(self.base_dir), photo_name)
        pix = QPixmap(photo_path)
        
        if not pix.isNull():
            self.photo.setPixmap(
                pix.scaled(self.photo.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            )
            self.photo.setText("")
        else:
            self.photo.setPixmap(QPixmap())
            self.photo.setText("Нет фото")

        try:
            t = user_row.get("software_start_time", "").split(":")
            self.start_time = datetime.datetime.now().replace(
                hour=int(t[0]), minute=int(t[1]), second=int(t[2])
            )
        except:
            self.start_time = datetime.datetime.now()

        self.lbl_start.setText(
            f"Время запуска ПО: <b>{self.start_time.strftime('%H:%M:%S')}</b>"
        )
        self.timer_monitor.start(1000)

    def _refresh_left_info(self):
        self.lbl_name.setText("Фамилия Имя Отчество")
        self.lbl_age.setText("Возраст")
        self.lbl_dt.setText("Дата/время: <b>00.00.0000 / 00:00:00</b>")
        self.lbl_start.setText("Время запуска ПО: <b>00:00:00</b>")
        self.lbl_drive.setText("Время в дороге: <b>00:00:00</b>")
        self.lbl_left.setText("Оставшееся время: <b>00:00:00</b>")
        self.lbl_status.setText("Состояние: ")

        default_pix_path = os.path.join(self.base_dir, "assets", "user.png")
        pix = QPixmap(default_pix_path)
        if not pix.isNull():
            self.photo.setPixmap(
                pix.scaled(self.photo.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            )
        else:
            self.photo.setText("Нет фото")

    def _update_monitor_data(self):
        pulse = 0
        status = ""
        drive_dur = "00:00:00"
        target_id = self.operator_data.get("id")

        if target_id:
            try:
                with open(utils._csv_path(), "r", newline="", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        if row.get("id") == target_id:
                            p_raw = row.get("current_pulse", "0")
                            pulse = int(p_raw) if p_raw.isdigit() else 0
                            status = row.get("operator_status", "")
                            drive_dur = row.get("drive_duration", "00:00:00")
                            break
            except:
                pass

        if not status:
            self._set_waiting_state()
            return

        self.current_status = status
        now = datetime.datetime.now()
        
        self.lbl_dt.setText(
            f"Дата/время: <b>{now.strftime('%d.%m.%Y')} / {now.strftime('%H:%M:%S')}</b>"
        )
        self.lbl_drive.setText(f"Время в дороге: <b>{drive_dur}</b>")

        seconds_done = utils._parse_hms_to_seconds(drive_dur)
        rem = max(0, 9 * 3600 - seconds_done)
        time_left_str = f"{rem // 3600:02d}:{(rem % 3600) // 60:02d}:{rem % 60:02d}"
        self.lbl_left.setText(f"Оставшееся время: <b>{time_left_str}</b>")

        self._update_indication_block(pulse)
        self._update_terminal_block(pulse)

    def _set_waiting_state(self):
        self.mid_info.setText(
            "Ожидание данных...\nОператор еще не перешел в режим «Управление»."
        )
        self.lbl_drive.setText("Время в дороге: <b>--:--:--</b>")
        self.lbl_left.setText("Оставшееся время: <b>--:--:--</b>")
        self.lbl_status.setText("Состояние: <span style='color:gray'>ОЖИДАНИЕ</span>")
        self.lbl_pulse_val.setText("--")
        
        inactive_style = "background-color: #C7C7C7; border: 2px solid #44CC29;"
        for sq in [self.lbl_sq_green, self.lbl_sq_yellow, self.lbl_sq_red]:
            sq.setStyleSheet(inactive_style)

    def _update_indication_block(self, pulse):
        self.lbl_pulse_val.setText(str(pulse) if pulse > 0 else "--")
        
        border_blue = "border: 2px solid #44CC29;"
        c_green, c_yellow, c_red, c_off = "#009900", "#FFD700", "#FF0000", "#C7C7C7"

        if self.current_status == "NORMAL":
            self.player_warning.stop()
            self.player_alarm.stop()
            
            self.lbl_status.setText("Состояние: <span style='color:green'>НОРМА</span>")
            self.lbl_pulse_val.setStyleSheet("color: #009900;")
            
            self.lbl_sq_green.setStyleSheet(f"background-color: {c_green}; {border_blue}")
            self.lbl_sq_yellow.setStyleSheet(c_off)
            self.lbl_sq_red.setStyleSheet(c_off)
            
            self.lbl_sq_green.set_color("#7CE4D5")
            self.lbl_sq_yellow.set_color(c_off)
            self.lbl_sq_red.set_color(c_off)

        elif self.current_status == "WARNING":
            if self.player_warning.state() != QMediaPlayer.PlayingState:
                self.player_warning.play()
            self.player_alarm.stop()
            
            self.lbl_status.setText("Состояние: <span style='color:#FFD700'>ВНИМАНИЕ</span>")
            self.lbl_pulse_val.setStyleSheet("color: #FFD700;")
            
            self.lbl_sq_green.setStyleSheet(c_off)
            self.lbl_sq_yellow.setStyleSheet(f"background-color: {c_yellow}; {border_blue}")
            self.lbl_sq_red.setStyleSheet(c_off)
            
            self.lbl_sq_green.set_color(c_off)
            self.lbl_sq_yellow.set_color("#FFD700")
            self.lbl_sq_red.set_color(c_off)

        elif self.current_status == "CRITICAL":
            self.player_warning.stop()
            if self.player_alarm.state() != QMediaPlayer.PlayingState:
                self.player_alarm.play()
                
            self.lbl_status.setText("Состояние: <span style='color:red'>КРИТИЧНО!</span>")
            self.lbl_pulse_val.setStyleSheet("color: red;")
            
            self.lbl_sq_green.setStyleSheet(c_off)
            self.lbl_sq_yellow.setStyleSheet(c_off)
            self.lbl_sq_red.setStyleSheet(f"background-color: {c_red}; {border_blue}")
            
            self.lbl_sq_green.set_color(c_off)
            self.lbl_sq_yellow.set_color(c_off)
            self.lbl_sq_red.set_color("#FF0000")

    def _update_terminal_block(self, pulse):
        p_str = str(pulse) if pulse > 0 else "--"
        
        if self.current_status == "NORMAL":
            msg = f"Состояние нормальное\nПульс {p_str}"
        elif self.current_status == "WARNING":
            msg = (f"Состояние оператора выходит за пределы «ВНИМАНИЕ»\n"
                   f"Пульс {p_str}\nЗапуск звукового оповещения «ВНИМАНИЕ»")
        elif self.current_status == "CRITICAL":
            msg = (f"Состояние критичное!\nПульс {p_str}\n"
                   f"Запуск звукового оповещения!")
        
        self.mid_info.setText(msg)

    def stop_program(self):
        self.timer_monitor.stop()
        self.player_warning.stop()
        self.player_alarm.stop()

        for sq in [self.lbl_sq_green, self.lbl_sq_yellow, self.lbl_sq_red]:
            sq.set_color("#C7C7C7")
            sq.setStyleSheet("background-color: white; border: 2px solid #44CC29;")

        self._refresh_left_info()
        self.mid_info.setText("")
        self.lbl_pulse_val.setText("")
        self.is_movable = False

        self.auth_window = AuthScreen(self)
        self.auth_window.position_over_terminal(self)
        self.auth_window.show()

    def _build_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_grey = QWidget()
        top_grey.setFixedHeight(30)
        top_layout = QHBoxLayout(top_grey)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("X")
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "color: #FF0000; border: none; font-size: 24px; font-weight: bold;"
        )
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_close)
        main_layout.addWidget(top_grey)

        top_line = QFrame()
        top_line.setFixedHeight(4)
        top_line.setStyleSheet("background-color: #FFFFFF;")
        main_layout.addWidget(top_line)

        header = QFrame()
        header.setFixedHeight(120)
        header.setStyleSheet("background-color: #44CC29;")
        
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 10, 0, 10)
        header_layout.setSpacing(5)

        title_main = QLabel("НейроБодр")
        title_main.setAlignment(Qt.AlignCenter)
        title_main.setStyleSheet("color: white;")
        title_main.setFont(QFont("Times New Roman", 40, QFont.Bold))
        header_layout.addWidget(title_main)
        
        line_layout = QHBoxLayout()
        line_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        logo_line = QFrame()
        logo_line.setFixedHeight(2)
        logo_line.setStyleSheet("background-color: white;")
        logo_line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line_layout.addWidget(logo_line, stretch=3)
        line_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        header_layout.addLayout(line_layout)
        
        title_sub = QLabel("Программа для мониторинга состояния водителей")
        title_sub.setAlignment(Qt.AlignCenter)
        title_sub.setStyleSheet("color: white;")
        title_sub.setFont(QFont("Times New Roman", 16))
        header_layout.addWidget(title_sub)
        
        main_layout.addWidget(header)

        header_bottom_line = QFrame()
        header_bottom_line.setFixedHeight(4)
        header_bottom_line.setStyleSheet("background-color: #FFFFFF;")
        main_layout.addWidget(header_bottom_line)

        body_container = QWidget()
        body_container.setStyleSheet("background-color: #FFFFFF;")
        
        body_main_layout = QVBoxLayout(body_container)
        body_main_layout.setContentsMargins(0, 0, 0, 0)
        body_main_layout.setSpacing(4)

        top_row = QWidget()
        top_row.setFixedHeight(44)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        left_header = QFrame(); left_header.setStyleSheet("background-color: #D9D9D9;")
        mid_header = QFrame(); mid_header.setStyleSheet("background-color: #D9D9D9;")
        right_header = QFrame(); right_header.setStyleSheet("background-color: #D9D9D9;")

        top_layout.addWidget(left_header, stretch=1)
        top_layout.addWidget(mid_header, stretch=1)
        top_layout.addWidget(right_header, stretch=1)

        lh_layout = QVBoxLayout(left_header)
        lbl_info = QLabel("Информация оператора")
        lbl_info.setAlignment(Qt.AlignCenter)
        lbl_info.setFont(QFont("Times New Roman", 14, QFont.Bold))
        lh_layout.addWidget(lbl_info)

        mh_layout = QVBoxLayout(mid_header)
        lbl_term = QLabel("Терминальный блок")
        lbl_term.setAlignment(Qt.AlignCenter)
        lbl_term.setFont(QFont("Times New Roman", 14, QFont.Bold))
        mh_layout.addWidget(lbl_term)
        
        rh_layout = QVBoxLayout(right_header)
        lbl_ind = QLabel("Блок индикации")
        lbl_ind.setAlignment(Qt.AlignCenter)
        lbl_ind.setFont(QFont("Times New Roman", 14, QFont.Bold))
        rh_layout.addWidget(lbl_ind)

        body_main_layout.addWidget(top_row)

        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)

        self.left = QFrame(); self.left.setStyleSheet("background-color: #D9D9D9;")
        self.mid = QFrame(); self.mid.setStyleSheet("background-color: black;")
        self.right = QFrame(); self.right.setStyleSheet("background-color: #D9D9D9;")

        bottom_layout.addWidget(self.left, stretch=1)
        bottom_layout.addWidget(self.mid, stretch=1)
        bottom_layout.addWidget(self.right, stretch=1)

        body_main_layout.addWidget(bottom_row, stretch=1)
        main_layout.addWidget(body_container, stretch=1)

        self._build_left_info()
        self._build_mid_info()
        self._build_right_info()

    def _build_left_info(self):
        left_layout = QVBoxLayout(self.left)
        left_layout.setContentsMargins(15, 10, 15, 10)
        left_layout.setSpacing(5)

        profile_layout = QHBoxLayout()
        self.photo = QLabel()
        self.photo.setFixedSize(90, 100)
        self.photo.setStyleSheet("background-color: white;")
        self.photo.setAlignment(Qt.AlignCenter)
        profile_layout.addWidget(self.photo)
        
        name_age_layout = QVBoxLayout()
        self.lbl_name = QLabel("Фамилия Имя Отчество")
        self.lbl_name.setFont(QFont("Times New Roman", 16))
        self.lbl_name.setWordWrap(True)
        name_age_layout.addWidget(self.lbl_name)
        
        self.lbl_age = QLabel("Возраст")
        self.lbl_age.setFont(QFont("Times New Roman", 16))
        name_age_layout.addWidget(self.lbl_age)
        
        profile_layout.addLayout(name_age_layout)
        profile_layout.addStretch()
        left_layout.addLayout(profile_layout)
        
        left_layout.addSpacing(15)

        font_labels = QFont("Times New Roman", 14)
        
        self.lbl_dt = QLabel("Дата/время: <b>00.00.0000 / 00:00:00</b>")
        self.lbl_dt.setFont(font_labels)
        left_layout.addWidget(self.lbl_dt)
        
        self.lbl_start = QLabel("Время запуска ПО: <b>00:00:00</b>")
        self.lbl_start.setFont(font_labels)
        left_layout.addWidget(self.lbl_start)
        
        self.lbl_drive = QLabel("Время в дороге: <b>00:00:00</b>")
        self.lbl_drive.setFont(font_labels)
        left_layout.addWidget(self.lbl_drive)
        
        self.lbl_left = QLabel("Оставшееся время: <b>00:00:00</b>")
        self.lbl_left.setFont(font_labels)
        left_layout.addWidget(self.lbl_left)
        
        self.lbl_status = QLabel("Состояние: ")
        self.lbl_status.setFont(font_labels)
        left_layout.addWidget(self.lbl_status)

        left_layout.addStretch()
        self._refresh_left_info()
        
    def _build_mid_info(self):
        mid_layout = QVBoxLayout(self.mid)
        mid_layout.setContentsMargins(20, 20, 20, 20)
        
        self.mid_info = QLabel("")
        self.mid_info.setStyleSheet("color: white; background: transparent;")
        self.mid_info.setFont(QFont("Consolas", 11))
        self.mid_info.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.mid_info.setWordWrap(True)
        
        mid_layout.addWidget(self.mid_info)

    def _build_right_info(self):
        right_layout = QVBoxLayout(self.right)
        right_layout.setContentsMargins(15, 20, 15, 20)
        
        pulse_layout = QHBoxLayout()
        lbl_pulse_title = QLabel("Пульс:")
        lbl_pulse_title.setFont(QFont("Times New Roman", 28, QFont.Bold))
        
        self.lbl_pulse_val = QLabel("--")
        self.lbl_pulse_val.setStyleSheet("color: #FF0000;")
        self.lbl_pulse_val.setFont(QFont("Times New Roman", 42, QFont.Bold))
        
        pulse_layout.addWidget(lbl_pulse_title)
        pulse_layout.addSpacing(10)
        pulse_layout.addWidget(self.lbl_pulse_val)
        pulse_layout.addStretch()
        
        right_layout.addLayout(pulse_layout)
        right_layout.addStretch()
        
        shapes_layout = QHBoxLayout()
        shapes_layout.setSpacing(10)
        self.lbl_sq_green = ShapeWidget("circle", "#C7C7C7")
        self.lbl_sq_yellow = ShapeWidget("triangle", "#C7C7C7")
        self.lbl_sq_red = ShapeWidget("square", "#C7C7C7")
        
        shapes_layout.addStretch()
        shapes_layout.addWidget(self.lbl_sq_green)
        shapes_layout.addWidget(self.lbl_sq_yellow)
        shapes_layout.addWidget(self.lbl_sq_red)
        shapes_layout.addStretch()
        
        right_layout.addLayout(shapes_layout)
        right_layout.addStretch()
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.btn_next = QPushButton("Стоп программа")
        self.btn_next.setFixedSize(130, 40)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet("""
            QPushButton { 
                background-color: #2C2C2C; 
                color: #FFFFFF; 
                border-radius: 6px; 
                font-size: 14px; 
                font-weight: 600; 
            } 
            QPushButton:hover { background-color: #44CC29; }
        """)
        self.btn_next.clicked.connect(self.stop_program)
        btn_layout.addWidget(self.btn_next)
        
        right_layout.addLayout(btn_layout)


if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    policy = Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(policy)

    app = QApplication(sys.argv)
    app.setFont(QFont("Times New Roman", 14))

    main_window = RemoteForm()
    screen_rect = QApplication.desktop().availableGeometry()
    win_x = (screen_rect.width() - main_window.width()) // 2
    win_y = (screen_rect.height() - main_window.height()) // 2
    main_window.move(win_x, win_y)
    main_window.show()

    auth_window = AuthScreen(main_window)
    auth_window.position_over_terminal(main_window)
    auth_window.show()

    sys.exit(app.exec_())