import sys
import os
import csv
import datetime
import utils
from PyQt5.QtCore import QPoint, Qt, QRegularExpression, QTimer, QUrl
from PyQt5.QtGui import QBrush, QColor, QFont, QPainter, QPixmap, QGuiApplication, QPolygon, QRegularExpressionValidator
from PyQt5.QtWidgets import QWidget, QLabel, QPushButton, QFrame, QApplication, QVBoxLayout, QHBoxLayout, QLineEdit, QMessageBox
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent, QMediaPlaylist

class ShapeWidget(QWidget):
    def __init__(self, shape_type, color, parent=None):
        super().__init__(parent)
        self.shape_type, self.color = shape_type, color
        self.setFixedSize(80, 80)

    def set_color(self, new_color):
        self.color = new_color
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(QColor(self.color)))
        if self.shape_type == "circle": painter.drawEllipse(0, 0, self.width(), self.height())
        elif self.shape_type == "triangle": painter.drawPolygon(QPolygon([QPoint(self.width() // 2, 0), QPoint(0, self.height()), QPoint(self.width(), self.height())]))
        elif self.shape_type == "square": painter.drawRect(0, 0, self.width(), self.height())

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

        top_grey = QWidget(self)
        top_grey.setFixedHeight(24)
        top_layout = QHBoxLayout(top_grey)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("×", top_grey)
        self.btn_close.setFixedSize(24, 24)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("color: #FF0000; border: none; font-size: 24px; font-weight: bold;")
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
        self.in_id.setStyleSheet("background-color: #FFFFFF; border: none; padding-left: 8px;")
        self.in_id.setValidator(QRegularExpressionValidator(QRegularExpression(r"\d+"), self))

        self.btn_login = QPushButton("Далее", self)
        self.btn_login.setFixedSize(100, 36)
        self.btn_login.setCursor(Qt.PointingHandCursor)
        self.btn_login.setStyleSheet("""
            QPushButton { background-color: #2C2C2C; color: #FFFFFF; border-radius: 6px; font-weight: 600; font-size: 13px; }
            QPushButton:hover { background-color: #44CC29; }
        """)
        self.btn_login.clicked.connect(self.on_login)

        row.addWidget(self.in_id, 1)
        row.addWidget(self.btn_login, 0)
        root.addLayout(row)

    def on_login(self):
        user_id = self.in_id.text().strip()
        if not user_id: return

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
        col_w = parent.W // 3
        abs_x = pgp.x() + col_w
        abs_y = pgp.y() + parent.FRAME_H + parent.HEADER_H + parent.SECTION_H
        self.move(abs_x + (col_w - self.width()) // 2, abs_y + (parent.BODY_H - parent.SECTION_H - self.height()) // 2)

class RemoteForm(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self._old_pos = None
        self.is_movable = False

        self.W, self.H, self.FRAME_H, self.HEADER_H, self.SECTION_H, self.GRID_T = 1000, 450, 34, 120, 44, 4
        self.BODY_H = self.H - self.HEADER_H

        self.setFixedSize(self.W, self.H + self.FRAME_H)
        self.setWindowTitle("Удаленный мониторинг")
        self.setStyleSheet("background-color: #D9D9D9;")
        self.base_dir = os.path.dirname(os.path.abspath(__file__))

        self.player_warning, self.player_alarm = QMediaPlayer(), QMediaPlayer()
        self.playlist_warn, self.playlist_alarm = QMediaPlaylist(), QMediaPlaylist()
        
        self.playlist_warn.addMedia(QMediaContent(QUrl.fromLocalFile("yellowSound.mp3")))
        self.playlist_warn.setPlaybackMode(QMediaPlaylist.Loop)
        self.player_warning.setPlaylist(self.playlist_warn)

        self.playlist_alarm.addMedia(QMediaContent(QUrl.fromLocalFile("redSound.mp3")))
        self.playlist_alarm.setPlaybackMode(QMediaPlaylist.Loop)
        self.player_alarm.setPlaylist(self.playlist_alarm)

        self.timer_monitor = QTimer(self)
        self.timer_monitor.timeout.connect(self._update_monitor_data)

        self.operator_data, self.start_time, self.current_status = {}, None, "NORMAL"
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

    def init_session(self, user_row):
        self.operator_data, self.is_movable = user_row, True
        self.lbl_name.setText(f"{user_row.get('last_name', '')} {user_row.get('first_name', '')}\n{user_row.get('middle_name', '')}")
        self.lbl_age.setText(f"{user_row.get('age', '')} лет")

        pix = QPixmap(os.path.join(utils._ensure_dirs(self.base_dir), f"ID_{utils._id_str(int(user_row.get('id', '0')))}.jpg"))
        if not pix.isNull():
            self.photo.setPixmap(pix.scaled(self.photo.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
            self.photo.setText("")
        else:
            self.photo.setPixmap(QPixmap())
            self.photo.setText("Нет фото")

        try:
            t = user_row.get("software_start_time", "").split(":")
            self.start_time = datetime.datetime.now().replace(hour=int(t[0]), minute=int(t[1]), second=int(t[2]))
        except:
            self.start_time = datetime.datetime.now()

        self.lbl_start.setText(f"Время запуска ПО: <b>{self.start_time.strftime('%H:%M:%S')}</b>")
        self.timer_monitor.start(1000)

    def _update_monitor_data(self):
        pulse, status, drive_dur = 0, "", "00:00:00"
        target_id = self.operator_data.get("id")

        if target_id:
            try:
                with open(utils._csv_path(), "r", newline="", encoding="utf-8") as f:
                    for row in csv.DictReader(f):
                        if row.get("id") == target_id:
                            pulse = int(row.get("current_pulse", "0")) if row.get("current_pulse", "0").isdigit() else 0
                            status, drive_dur = row.get("operator_status", ""), row.get("drive_duration", "00:00:00")
                            break
            except: pass

        if not status:
            self.mid_info.setText("Ожидание данных...\nОператор еще не перешел в режим «Управление».")
            self.lbl_drive.setText("Время в дороге: <b>--:--:--</b>")
            self.lbl_left.setText("Оставшееся время: <b>--:--:--</b>")
            self.lbl_status.setText("Состояние: <span style='color:gray'>ОЖИДАНИЕ</span>")
            self.lbl_pulse_val.setText("--")
            for sq in [self.lbl_sq_green, self.lbl_sq_yellow, self.lbl_sq_red]: sq.setStyleSheet("background-color: #D0CECF; border: 2px solid #0000FF;")
            return

        self.current_status = status
        now = datetime.datetime.now()
        self.lbl_dt.setText(f"Дата/время: <b>{now.strftime('%d.%m.%Y')} / {now.strftime('%H:%M:%S')}</b>")
        self.lbl_drive.setText(f"Время в дороге: <b>{drive_dur}</b>")

        rem = max(0, 9 * 3600 - utils._parse_hms_to_seconds(drive_dur))
        self.lbl_left.setText(f"Оставшееся время: <b>{rem // 3600:02d}:{(rem % 3600) // 60:02d}:{rem % 60:02d}</b>")

        self._update_indication_block(pulse)
        self._update_terminal_block(pulse)

    def _update_indication_block(self, pulse):
        self.lbl_pulse_val.setText(str(pulse) if pulse > 0 else "--")
        cb = "border: 2px solid #0000FF;"
        c_green, c_yellow, c_red, c_off = "#07D40B", "#FFFC00", "#D0021B", "#D0CECF"

        if self.current_status == "NORMAL":
            self.player_warning.stop()
            self.player_alarm.stop()
            self.lbl_status.setText("Состояние: <span style='color:green'>НОРМА</span>")
            self.lbl_pulse_val.setStyleSheet("color: #009900;")
            
            self.lbl_sq_green.setStyleSheet(f"background-color: {c_green}; {cb}")
            self.lbl_sq_yellow.setStyleSheet(c_off)
            self.lbl_sq_red.setStyleSheet(c_off)
            self.lbl_sq_green.set_color("#7CE4D5")
            self.lbl_sq_yellow.set_color(c_off)
            self.lbl_sq_red.set_color(c_off)

        elif self.current_status == "WARNING":
            if self.player_warning.state() != QMediaPlayer.PlayingState: self.player_warning.play()
            self.player_alarm.stop()
            self.lbl_status.setText("Состояние: <span style='color:#FFD700'>ВНИМАНИЕ</span>")
            self.lbl_pulse_val.setStyleSheet("color: #FFD700;")
            
            self.lbl_sq_green.setStyleSheet(c_off)
            self.lbl_sq_yellow.setStyleSheet(f"background-color: {c_yellow}; {cb}")
            self.lbl_sq_red.setStyleSheet(c_off)
            self.lbl_sq_green.set_color(c_off)
            self.lbl_sq_yellow.set_color("#F9D849")
            self.lbl_sq_red.set_color(c_off)

        elif self.current_status == "CRITICAL":
            self.player_warning.stop()
            if self.player_alarm.state() != QMediaPlayer.PlayingState: self.player_alarm.play()
            self.lbl_status.setText("Состояние: <span style='color:red'>КРИТИЧНО!</span>")
            self.lbl_pulse_val.setStyleSheet("color: red;")
            
            self.lbl_sq_green.setStyleSheet(c_off)
            self.lbl_sq_yellow.setStyleSheet(c_off)
            self.lbl_sq_red.setStyleSheet(f"background-color: {c_red}; {cb}")
            self.lbl_sq_green.set_color(c_off)
            self.lbl_sq_yellow.set_color(c_off)
            self.lbl_sq_red.set_color("#D0021B")

    def _update_terminal_block(self, pulse):
        p_str = str(pulse) if pulse > 0 else "--"
        if self.current_status == "NORMAL":
            self.mid_info.setText(f"Состояние нормальное\nПульс {p_str}")
        elif self.current_status == "WARNING":
            self.mid_info.setText(f"Состояние оператора выходит за пределы «ВНИМАНИЕ»\nПульс {p_str}\nЗапуск звукового оповещения «ВНИМАНИЕ»")
        elif self.current_status == "CRITICAL":
            self.mid_info.setText(f"Состояние критичное!\nПульс {p_str}\nЗапуск звукового оповещения!")

    def stop_program(self):
        self.timer_monitor.stop()
        self.player_warning.stop()
        self.player_alarm.stop()

        for sq in [self.lbl_sq_green, self.lbl_sq_yellow, self.lbl_sq_red]:
            sq.set_color("white")
            sq.setStyleSheet("background-color: white; border: 2px solid #0000FF;")

        self._refresh_left_info()
        self.mid_info.setText("")
        self.lbl_pulse_val.setText("")
        self.is_movable = False

        self.auth_window = AuthScreen(self)
        self.auth_window.position_over_terminal(self)
        self.auth_window.show()

    def _build_ui(self):
        top_grey = QWidget(self)
        top_grey.setGeometry(0, 0, self.W, 30)
        top_layout = QHBoxLayout(top_grey)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("×", top_grey)
        self.btn_close.setFixedSize(30, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("color: #FF0000; border: none; font-size: 36px; font-weight: bold;")
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_close)

        top_line = QFrame(self)
        top_line.setGeometry(0, 30, self.W, 4)
        top_line.setStyleSheet("background-color: #FFFFFF;")

        header = QFrame(self)
        header.setGeometry(0, self.FRAME_H, self.W, self.HEADER_H)
        header.setStyleSheet("background-color: #44CC29;")

        QLabel("НейроБодр", header).setGeometry(0, 6, self.W, 62)
        
        logo_line = QFrame(header)
        logo_line.setGeometry(int(self.W * 0.16), 76, int(self.W * 0.68), 2)
        logo_line.setStyleSheet("background-color: white;")
        
        QLabel("Программа для мониторинга состояния водителей", header).setGeometry(0, 80, self.W, 30)

        for lbl in header.findChildren(QLabel):
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: white;")
            lbl.setFont(QFont("Times New Roman", 40 if "НейроБодр" in lbl.text() else 16, QFont.Bold if "НейроБодр" in lbl.text() else QFont.Normal))

        header_bottom = QFrame(self)
        header_bottom.setGeometry(0, self.FRAME_H + self.HEADER_H - self.GRID_T, self.W, self.GRID_T)
        header_bottom.setStyleSheet("background-color: #FFFFFF;")
        header_bottom.raise_()

        body = QFrame(self)
        body.setGeometry(0, self.FRAME_H + self.HEADER_H, self.W, self.BODY_H)

        col_w = self.W // 3
        
        self.left = QFrame(body)
        self.left.setGeometry(0, 0, col_w, self.BODY_H)
        self.left.setStyleSheet("background-color: #D9D9D9;")

        self.mid = QFrame(body)
        self.mid.setGeometry(col_w, 0, col_w, self.BODY_H)
        self.mid.setStyleSheet("background-color: black;")

        self.right = QFrame(body)
        self.right.setGeometry(col_w * 2, 0, self.W - col_w * 2, self.BODY_H)
        self.right.setStyleSheet("background-color: #D9D9D9;")

        self._section_header(self.left, "Информация оператора", col_w)
        self._section_header(self.mid, "Терминальный блок", col_w)
        self._section_header(self.right, "Блок индикации", self.W - col_w * 2)

        self._build_left_info(col_w)

        self.mid_info = QLabel("", self.mid)
        self.mid_info.setGeometry(20, self.SECTION_H + 20, col_w - 40, 150)
        self.mid_info.setStyleSheet("color: white;")
        self.mid_info.setFont(QFont("Consolas", 11))
        self.mid_info.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.mid_info.setWordWrap(True)

        lbl_pulse_title = QLabel("Пульс:", self.right)
        lbl_pulse_title.setGeometry(20, self.SECTION_H + 20, 120, 50)
        lbl_pulse_title.setFont(QFont("Times New Roman", 28, QFont.Bold))

        self._draw_shapes(self.right)
        self.lbl_pulse_val = QLabel("", self.right)
        self.lbl_pulse_val.setGeometry(150, self.SECTION_H + 15, 100, 60)
        self.lbl_pulse_val.setStyleSheet("color: #D32F2F;")
        self.lbl_pulse_val.setFont(QFont("Times New Roman", 42, QFont.Bold))

        self.btn_next = QPushButton("Стоп программа", self.right)
        self.btn_next.setGeometry(self.W - col_w * 2 - 150, self.BODY_H - 60, 130, 40)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet("QPushButton { background-color: #2C2C2C; color: #FFFFFF; border-radius: 6px; font-size: 14px; font-weight: 600; } QPushButton:hover { background-color: #44CC29; }")
        self.btn_next.clicked.connect(self.stop_program)

        for x in (col_w, col_w * 2):
            v_sep = QFrame(body)
            v_sep.setGeometry(x - 2, 0, 4, self.BODY_H)
            v_sep.setStyleSheet("background-color: #FFFFFF;")
            v_sep.raise_()
            
        h_sep = QFrame(body)
        h_sep.setGeometry(0, self.SECTION_H, self.W, 4)
        h_sep.setStyleSheet("background-color: #FFFFFF;")
        h_sep.raise_()

    def _section_header(self, parent, text, w):
        lbl = QLabel(text, QFrame(parent))
        lbl.setGeometry(0, 0, w, self.SECTION_H)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Times New Roman", 14, QFont.Bold))
        lbl.parent().setGeometry(0, 0, w, self.SECTION_H)
        lbl.parent().setStyleSheet("background-color: #D9D9D9;")

    def _build_left_info(self, col_w):
        y, text_x = self.SECTION_H + 20, 118
        
        self.photo = QLabel(self.left)
        self.photo.setGeometry(10, y, 90, 100)
        self.photo.setStyleSheet("background-color: white;")
        self.photo.setAlignment(Qt.AlignCenter)

        self.lbl_name = QLabel(self.left)
        self.lbl_name.setGeometry(text_x, y + 5, col_w - text_x - 18, 70)
        self.lbl_name.setFont(QFont("Times New Roman", 16))
        self.lbl_name.setWordWrap(True)

        self.lbl_age = QLabel(self.left)
        self.lbl_age.setGeometry(text_x, y + 70, col_w - text_x - 18, 28)
        self.lbl_age.setFont(QFont("Times New Roman", 16))

        y2 = y + 105
        labels = ["lbl_dt", "lbl_start", "lbl_drive", "lbl_left", "lbl_status"]
        for i, attr in enumerate(labels):
            lbl = QLabel(self.left)
            lbl.setGeometry(18, y2 + 30 * i, col_w - 36, 26)
            lbl.setFont(QFont("Times New Roman", 14))
            setattr(self, attr, lbl)

        self._refresh_left_info()

    def _refresh_left_info(self):
        self.lbl_name.setText("Фамилия Имя Отчество")
        self.lbl_age.setText("Возраст")
        self.lbl_dt.setText("Дата/время: <b>00.00.0000 / 00:00:00</b>")
        self.lbl_start.setText("Время запуска ПО: <b>00:00:00</b>")
        self.lbl_drive.setText("Время в дороге: <b>00:00:00</b>")
        self.lbl_left.setText("Оставшееся время: <b>00:00:00</b>")
        self.lbl_status.setText("Состояние: ")

        pix = QPixmap(os.path.join(self.base_dir, "assets", "user.png"))
        if not pix.isNull(): self.photo.setPixmap(pix.scaled(self.photo.size(), Qt.IgnoreAspectRatio, Qt.SmoothTransformation))
        else: self.photo.setText("Нет фото")

    def _draw_shapes(self, parent):
        cx, cy = parent.geometry().width() // 2, parent.geometry().height() // 2 + 20
        xs = cx - 130

        self.lbl_sq_green = ShapeWidget("circle", "white", parent)
        self.lbl_sq_green.move(xs, cy - 40)
        self.lbl_sq_yellow = ShapeWidget("triangle", "white", parent)
        self.lbl_sq_yellow.move(xs + 90, cy - 40)
        self.lbl_sq_red = ShapeWidget("square", "white", parent)
        self.lbl_sq_red.move(xs + 180, cy - 40)

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    QGuiApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)

    app = QApplication(sys.argv)
    app.setFont(QFont("Times New Roman", 14))

    main_window = RemoteForm()
    rect = QApplication.desktop().availableGeometry()
    main_window.move((rect.width() - main_window.width()) // 2, (rect.height() - main_window.height()) // 2)
    main_window.show()

    auth_window = AuthScreen(main_window)
    auth_window.position_over_terminal(main_window)
    auth_window.show()

    sys.exit(app.exec_())