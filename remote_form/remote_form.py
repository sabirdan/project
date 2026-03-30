import sys
import os
import datetime

from PyQt5.QtCore import QPoint, Qt, QRegularExpression, QTimer, QUrl
from PyQt5.QtGui import QFont, QPixmap, QGuiApplication, QRegularExpressionValidator
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QApplication, 
    QVBoxLayout, QHBoxLayout, QMessageBox, QSpacerItem, QSizePolicy
)
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist

from utils import (
    BaseWindow, ShapeWidget, create_label, csv_path, id_str, 
    ensure_dirs, parse_hms_to_seconds, find_operator_by_id,
    COLOR_BG, COLOR_GREEN, COLOR_BTN_BG, COLOR_DISABLED,
    create_line_edit, getbtn_style
)

class AuthScreen(BaseWindow):
    def __init__(self, remote_form):
        super().__init__(310, 150, "Авторизация")
        self.remote_form = remote_form
        self.setWindowModality(Qt.ApplicationModal)

        root = QVBoxLayout(self.content_container)
        root.setContentsMargins(15, 15, 15, 15)

        title = create_label("Введите ID_оператора", 16)
        root.addWidget(title, alignment=Qt.AlignLeft | Qt.AlignTop)
        root.addStretch(1)

        row = QHBoxLayout()
        row.setSpacing(10)

        self.in_id = create_line_edit(height=36, font_size=18, padding=8)
        self.in_id.setValidator(
            QRegularExpressionValidator(QRegularExpression(r"\d+"), self)
        )

        self.btn_login = QPushButton("Далее", self)
        self.btn_login.setFixedSize(100, 36)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet(getbtn_style())
        self.btn_login.clicked.connect(self.on_login)

        row.addWidget(self.in_id, 1)
        row.addWidget(self.btn_login, 0)
        root.addLayout(row)

    def on_login(self):
        user_id = self.in_id.text().strip()
        if not user_id:
            return

        found_user = find_operator_by_id(csv_path(), int(user_id))

        if found_user:
            self.remote_form.init_session(found_user)
            self.remote_form.show()
            self.close()
        else:
            QMessageBox.warning(self, "Ошибка", "Оператор с таким ID не найден")

    def position_over_terminal(self, parent):
        pgp = parent.mapToGlobal(QPoint(0, 0))
        abs_x = pgp.x() + (parent.width() // 3)
        abs_y = pgp.y() + 34 + 120 + 44 
        
        target_x = abs_x + ((parent.width() // 3) - self.width()) // 2
        target_y = abs_y + (286 - self.height()) // 2
        
        self.move(target_x, target_y)

class RemoteForm(BaseWindow):
    def __init__(self):
        super().__init__(1000, 484, "Удаленный мониторинг")
        
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
        self.timer_monitor.timeout.connect(self.update_monitor_data)

        self.operator_data = {}
        self.start_time = None
        self.current_status = "NORMAL"
        self.auth_window = None

        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.build_ui(content_layout)

    def mouse_press_event(self, event):
        if self.is_movable and event.button() == Qt.LeftButton and event.y() <= 34:
            self._old_pos = event.globalPos()

    def mouse_move_event(self, event):
        if self.is_movable and self._old_pos is not None:
            delta = QPoint(event.globalPos() - self._old_pos)
            self.move(self.x() + delta.x(), self.y() + delta.y())
            self._old_pos = event.globalPos()

    def mouse_release_event(self, event):
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

        photo_name = f"ID_{id_str(int(user_row.get('id', '0')))}.jpg"
        photo_path = os.path.join(ensure_dirs(self.base_dir), photo_name)
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

        self.lbl_start.setText(f"Время запуска ПО: <b>{self.start_time.strftime('%H:%M:%S')}</b>")
        self.timer_monitor.start(1000)

    def refresh_left_info(self):
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

    def update_monitor_data(self):
        target_id = self.operator_data.get("id")
        if not target_id:
            return

        fresh_data = find_operator_by_id(csv_path(), int(target_id))
        
        pulse = 0
        status = "NORMAL"
        drive_dur = "00:00:00"

        if fresh_data:
            p_raw = fresh_data.get("current_pulse", "0")
            pulse = int(p_raw) if p_raw.isdigit() else 0
            status = fresh_data.get("operator_status", "NORMAL")
            drive_dur = fresh_data.get("drive_duration", "00:00:00")

        self.current_status = status
        now = datetime.datetime.now()
        
        self.lbl_dt.setText(
            f"Дата/время: <b>{now.strftime('%d.%m.%Y')} / {now.strftime('%H:%M:%S')}</b>"
        )
        self.lbl_drive.setText(f"Время в дороге: <b>{drive_dur}</b>")

        seconds_done = parse_hms_to_seconds(drive_dur)
        rem = max(0, 9 * 3600 - seconds_done)
        time_left_str = f"{rem // 3600:02d}:{(rem % 3600) // 60:02d}:{rem % 60:02d}"
        self.lbl_left.setText(f"Оставшееся время: <b>{time_left_str}</b>")

        self.update_indication_block(pulse)
        self.update_terminal_block(pulse)

    def update_indication_block(self, pulse):
        self.lbl_pulse_val.setText(str(pulse) if pulse > 0 else "--")
        border_blue = f"border: 2px solid {COLOR_GREEN};"

        if self.current_status == "NORMAL":
            self.player_warning.stop()
            self.player_alarm.stop()
            
            self.lbl_status.setText(f"Состояние: <span style='color: green'>НОРМА</span>")
            self.lbl_pulse_val.setStyleSheet(f"color: green;")
            
            self.lbl_sq_green.setStyleSheet(f"background-color: turquoise; {border_blue}")
            self.lbl_sq_yellow.setStyleSheet(COLOR_DISABLED)
            self.lbl_sq_red.setStyleSheet(COLOR_DISABLED)
            
            self.lbl_sq_green.set_color("turquoise")
            self.lbl_sq_yellow.set_color(COLOR_DISABLED)
            self.lbl_sq_red.set_color(COLOR_DISABLED)

        elif self.current_status == "WARNING":
            if self.player_warning.state() != QMediaPlayer.PlayingState:
                self.player_warning.play()
            self.player_alarm.stop()
            
            self.lbl_status.setText(f"Состояние: <span style='color: gold'>ВНИМАНИЕ</span>")
            self.lbl_pulse_val.setStyleSheet(f"color: gold;")
            
            self.lbl_sq_green.setStyleSheet(COLOR_DISABLED)
            self.lbl_sq_yellow.setStyleSheet(f"background-color: gold; {border_blue}")
            self.lbl_sq_red.setStyleSheet(COLOR_DISABLED)
            
            self.lbl_sq_green.set_color(COLOR_DISABLED)
            self.lbl_sq_yellow.set_color("gold")
            self.lbl_sq_red.set_color(COLOR_DISABLED)

        elif self.current_status == "CRITICAL":
            self.player_warning.stop()
            if self.player_alarm.state() != QMediaPlayer.PlayingState:
                self.player_alarm.play()
                
            self.lbl_status.setText(f"Состояние: <span style='color: red'>КРИТИЧНО!</span>")
            self.lbl_pulse_val.setStyleSheet(f"color: red;")
            
            self.lbl_sq_green.setStyleSheet(COLOR_DISABLED)
            self.lbl_sq_yellow.setStyleSheet(COLOR_DISABLED)
            self.lbl_sq_red.setStyleSheet(f"background-color: red; {border_blue}")
            
            self.lbl_sq_green.set_color(COLOR_DISABLED)
            self.lbl_sq_yellow.set_color(COLOR_DISABLED)
            self.lbl_sq_red.set_color("red")

    def update_terminal_block(self, pulse):
        p_str = str(pulse) if pulse > 0 else "--"
        
        if self.current_status == "NORMAL":
            msg = f"Состояние нормальное\nПульс {p_str}"
        elif self.current_status == "WARNING":
            msg = (f"Состояние оператора выходит за пределы «ВНИМАНИЕ»\n"
                   f"Пульс {p_str}\nЗапуск звукового оповещения «ВНИМАНИЕ»")
        elif self.current_status == "CRITICAL":
            msg = (f"Состояние критичное!\nПульс {p_str}\nЗапуск звукового оповещения!")
        
        self.mid_info.setText(msg)

    def stop_program(self):
        self.timer_monitor.stop()
        self.player_warning.stop()
        self.player_alarm.stop()

        for sq in [self.lbl_sq_green, self.lbl_sq_yellow, self.lbl_sq_red]:
            sq.set_color(COLOR_DISABLED)
            sq.setStyleSheet(f"background-color: white; border: 2px solid {COLOR_GREEN};")

        self.refresh_left_info()
        self.mid_info.setText("")
        self.lbl_pulse_val.setText("")
        self.is_movable = False

        self.auth_window = AuthScreen(self)
        self.auth_window.position_over_terminal(self)
        self.auth_window.show()

    def build_ui(self, parent_layout):
        header = QFrame()
        header.setFixedHeight(120)
        header.setStyleSheet(f"background-color: {COLOR_GREEN};")
        
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 10, 0, 10)
        header_layout.setSpacing(5)

        title_main = create_label("НейроБодр", 40, bold=True, color="white", align=Qt.AlignCenter)
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
        
        title_sub = create_label("Программа для мониторинга состояния водителей", 16, color="white", align=Qt.AlignCenter)
        header_layout.addWidget(title_sub)
        
        parent_layout.addWidget(header)

        header_bottom_line = QFrame()
        header_bottom_line.setFixedHeight(4)
        header_bottom_line.setStyleSheet("background-color: white;")
        parent_layout.addWidget(header_bottom_line)

        body_container = QWidget()
        body_container.setStyleSheet("background-color: white;")
        
        body_main_layout = QVBoxLayout(body_container)
        body_main_layout.setContentsMargins(0, 0, 0, 0)
        body_main_layout.setSpacing(4)

        top_row = QWidget()
        top_row.setFixedHeight(44)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        left_header = QFrame(); left_header.setStyleSheet(f"background-color: {COLOR_BG};")
        mid_header = QFrame(); mid_header.setStyleSheet(f"background-color: {COLOR_BG};")
        right_header = QFrame(); right_header.setStyleSheet(f"background-color: {COLOR_BG};")

        top_layout.addWidget(left_header, stretch=1)
        top_layout.addWidget(mid_header, stretch=1)
        top_layout.addWidget(right_header, stretch=1)

        lh_layout = QVBoxLayout(left_header)
        lbl_info = create_label("Информация оператора", 14, bold=True, align=Qt.AlignCenter)
        lh_layout.addWidget(lbl_info)

        mh_layout = QVBoxLayout(mid_header)
        lbl_term = create_label("Терминальный блок", 14, bold=True, align=Qt.AlignCenter)
        mh_layout.addWidget(lbl_term)
        
        rh_layout = QVBoxLayout(right_header)
        lbl_ind = create_label("Блок индикации", 14, bold=True, align=Qt.AlignCenter)
        rh_layout.addWidget(lbl_ind)

        body_main_layout.addWidget(top_row)

        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)

        self.left = QFrame(); self.left.setStyleSheet(f"background-color: {COLOR_BG};")
        self.mid = QFrame(); self.mid.setStyleSheet(f"background-color: {COLOR_BTN_BG};")
        self.right = QFrame(); self.right.setStyleSheet(f"background-color: {COLOR_BG};")

        bottom_layout.addWidget(self.left, stretch=1)
        bottom_layout.addWidget(self.mid, stretch=1)
        bottom_layout.addWidget(self.right, stretch=1)

        body_main_layout.addWidget(bottom_row, stretch=1)
        parent_layout.addWidget(body_container, stretch=1)

        self.build_left_info()
        self.build_mid_info()
        self.build_right_info()

    def build_left_info(self):
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
        self.lbl_name = create_label("Фамилия Имя Отчество", 16)
        self.lbl_name.setWordWrap(True)
        name_age_layout.addWidget(self.lbl_name)
        
        self.lbl_age = create_label("Возраст", 16)
        name_age_layout.addWidget(self.lbl_age)
        
        profile_layout.addLayout(name_age_layout)
        profile_layout.addStretch()
        left_layout.addLayout(profile_layout)
        
        left_layout.addSpacing(15)

        self.lbl_dt = create_label("Дата/время: <b>00.00.0000 / 00:00:00</b>", 14)
        left_layout.addWidget(self.lbl_dt)
        
        self.lbl_start = create_label("Время запуска ПО: <b>00:00:00</b>", 14)
        left_layout.addWidget(self.lbl_start)
        
        self.lbl_drive = create_label("Время в дороге: <b>00:00:00</b>", 14)
        left_layout.addWidget(self.lbl_drive)
        
        self.lbl_left = create_label("Оставшееся время: <b>00:00:00</b>", 14)
        left_layout.addWidget(self.lbl_left)
        
        self.lbl_status = create_label("Состояние: ", 14)
        left_layout.addWidget(self.lbl_status)

        left_layout.addStretch()
        self.refresh_left_info()
        
    def build_mid_info(self):
        mid_layout = QVBoxLayout(self.mid)
        mid_layout.setContentsMargins(20, 20, 20, 20)
        
        self.mid_info = create_label("", 11, color="white", align=Qt.AlignLeft | Qt.AlignTop)
        self.mid_info.setFont(QFont("Consolas", 11))
        self.mid_info.setWordWrap(True)
        
        mid_layout.addWidget(self.mid_info)

    def build_right_info(self):
        right_layout = QVBoxLayout(self.right)
        right_layout.setContentsMargins(15, 20, 15, 20)
        
        pulse_layout = QHBoxLayout()
        lbl_pulse_title = create_label("Пульс:", 28, bold=True)
        
        self.lbl_pulse_val = create_label("", 42, bold=True, color="red")
        
        pulse_layout.addWidget(lbl_pulse_title)
        pulse_layout.addSpacing(10)
        pulse_layout.addWidget(self.lbl_pulse_val)
        pulse_layout.addStretch()
        
        right_layout.addLayout(pulse_layout)
        right_layout.addStretch()
        
        shapes_layout = QHBoxLayout()
        shapes_layout.setSpacing(10)
        self.lbl_sq_green = ShapeWidget("circle", COLOR_DISABLED, size=80)
        self.lbl_sq_yellow = ShapeWidget("triangle", COLOR_DISABLED, size=80)
        self.lbl_sq_red = ShapeWidget("square", COLOR_DISABLED, size=80)
        
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
        self.btn_next.setStyleSheet(getbtn_style())
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