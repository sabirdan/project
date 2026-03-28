import os
import re
import csv
import cv2
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QLineEdit, QFrame, QMessageBox, QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout
)

from utils import (
    _make_icon, _id_str, _next_id, _safe_csv_cell, _now_date_str, 
    _now_time_str, _draw_to_label_with_dpr, _opencv_save_jpg,
    get_cv_face, cv_find_match, cv_load_known_faces
)


class RegistrationForm(QWidget):
    def __init__(self, start_screen, csv_file: str, ops_dir: str, software_start_time: str):
        super().__init__()
        
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.start_screen = start_screen
        self.csv_file = csv_file
        self.ops_dir = ops_dir
        self.software_start_time = software_start_time

        self.current_id = None
        self.cap = None
        self._known_enc_cache = None
        self.last_frame = None
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._grab_frame)

        self.W = 1000
        self.H = 450
        self.HEADER_H = 120
        self.SECTION_H = 44
        self.GRID_T = 4
        self.BODY_H = self.H - self.HEADER_H

        self.setFixedSize(self.W, self.H + 34)
        self.setWindowTitle("НейроБодр")
        self.setStyleSheet("background-color: #D9D9D9;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        top_grey = QWidget(self)
        top_grey.setFixedHeight(30)
        top_layout = QHBoxLayout(top_grey)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("X", top_grey)
        self.btn_close.setFixedSize(45, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet(
            "color: #FF0000; border: none; font-size: 24px; font-weight: bold;"
        )
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_close)
        
        main_layout.addWidget(top_grey)

        top_white = QWidget(self)
        top_white.setFixedHeight(4)
        top_white.setStyleSheet("background-color: #FFFFFF;")
        main_layout.addWidget(top_white)

        self.content_container = QWidget(self)
        self.content_container.setFixedSize(self.W, self.H)
        main_layout.addWidget(self.content_container)

        self._build_ui()
        self._set_status(False, assigned=False)

    def reset_form(self):
        self.current_id = None
        self._known_enc_cache = None
        self.last_frame = None
        
        inputs = (self.in_last, self.in_first, self.in_middle, self.in_age)
        for inp in inputs:
            inp.clear()
        
        self._set_status(False, assigned=False)
        self.btn_next.setEnabled(False)
        self.btn_identify.setEnabled(False)
        
        default_pix = QPixmap("assets/face.png")
        self.cam_view.setPixmap(
            default_pix.scaled(self.cam_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _build_ui(self):
        header = QFrame(self.content_container)
        header.setGeometry(0, 0, self.W, self.HEADER_H)
        header.setStyleSheet("background-color: #44CC29;")

        t1 = QLabel("НейроБодр", header)
        t1.setGeometry(0, 6, self.W, 62)
        t1.setFont(QFont("Times New Roman", 40, QFont.Bold))
        t1.setStyleSheet("color: white;")
        t1.setAlignment(Qt.AlignCenter)

        line = QFrame(header)
        line.setGeometry(int(self.W * 0.16), 76, int(self.W * 0.68), 2)
        line.setStyleSheet("background-color: white;")

        t2_text = "Программа для мониторинга состояния водителей"
        t2 = QLabel(t2_text, header)
        t2.setGeometry(0, 80, self.W, 30)
        t2.setFont(QFont("Times New Roman", 16))
        t2.setStyleSheet("color: white;")
        t2.setAlignment(Qt.AlignCenter)

        body = QFrame(self.content_container)
        body.setGeometry(0, self.HEADER_H, self.W, self.BODY_H)

        col_w = self.W // 3
        col3_w = self.W - col_w * 2

        self.left = QFrame(body)
        self.left.setGeometry(0, 0, col_w, self.BODY_H)
        
        self.mid = QFrame(body)
        self.mid.setGeometry(col_w, 0, col_w, self.BODY_H)

        self.right = QFrame(body)
        self.right.setGeometry(col_w * 2, 0, col3_w, self.BODY_H)

        self._section_header(self.left, "Регистрация оператора", col_w)
        self._section_header(self.right, "Информационный блок", col3_w)

        self.btn_identify = QPushButton("Идентификация", self.mid)
        btn_x = (col_w - 200) // 2
        btn_y = (self.SECTION_H - 35) // 2
        self.btn_identify.setGeometry(btn_x, btn_y, 200, 35)
        self.btn_identify.setStyleSheet("""
            QPushButton { 
                background-color: #2C2C2C; 
                color: #FFFFFF; 
                border-radius: 6px; 
                font-size: 16px; 
            }
            QPushButton:hover { background-color: #44CC29; }
            QPushButton:disabled { background-color: #BDBDBD; color: #6B6B6B; }
        """)
        self.btn_identify.clicked.connect(self._on_identify_clicked)

        y0 = self.SECTION_H + 30
        field_step = 48
        
        self.in_last = self._labeled_input(self.left, "Фамилия", 18, y0, col_w)
        self.in_first = self._labeled_input(self.left, "Имя", 18, y0 + field_step, col_w)
        self.in_middle = self._labeled_input(self.left, "Отчество", 18, y0 + field_step * 2, col_w)
        self.in_age = self._labeled_input(self.left, "Возраст", 18, y0 + field_step * 3, col_w)

        btn_y_level = y0 + field_step * 3 + 61
        self.btn_save = self._small_btn(
            "Записать", self.left, col_w - 138, btn_y_level, self._on_save
        )
        self.btn_next = self._small_btn(
            "Далее", self.right, col3_w - 130, btn_y_level, self._go_start
        )

        cam_w = col_w - 25
        cam_h = 220
        cam_x = (col_w - cam_w) // 2
        cam_y = self.SECTION_H + (self.BODY_H - self.SECTION_H - cam_h) // 2
        
        self.cam_view = QLabel(self.mid)
        self.cam_view.setGeometry(cam_x, cam_y, cam_w, cam_h)
        self.cam_view.setAlignment(Qt.AlignCenter)

        rw = col3_w - 60
        self.status_text = QLabel(self.right)
        self.status_text.setGeometry(30, y0, rw - 34, 36)
        self.status_text.setFont(QFont("Times New Roman", 14))

        self.status_icon = QLabel(self.right)
        self.status_icon.setGeometry(30 + rw - 28, y0 + 4, 28, 28)

        self.id_banner = QLabel(self.right)
        self.id_banner.setGeometry(30, y0 + 60, rw, 46)
        self.id_banner.setFont(QFont("Times New Roman", 18, QFont.Bold))
        self.id_banner.setAlignment(Qt.AlignCenter)

        self.info_hint = QLabel(self.right)
        self.info_hint.setGeometry(30, y0 + 120, rw, 60)
        self.info_hint.setFont(QFont("Times New Roman", 14))

        self._grid(body, col_w)

    def _small_btn(self, text, parent, x, y, callback):
        btn = QPushButton(text, parent)
        w = 120 if text == "Записать" else 100
        btn.setGeometry(x, y, w, 34)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet("""
            QPushButton { 
                background-color: #2C2C2C; 
                color: #FFFFFF; 
                border-radius: 6px; 
                font-weight: 600; 
            }
            QPushButton:hover { background-color: #44CC29; }
            QPushButton:disabled { background-color: #BDBDBD; color: #6B6B6B; }
        """)
        btn.clicked.connect(callback)
        return btn

    def _grid(self, body, col_w):
        for x in (col_w, col_w * 2):
            sep = QFrame(body)
            sep.setGeometry(x - self.GRID_T // 2, 0, self.GRID_T, self.BODY_H)
            sep.setStyleSheet("background-color: #FFFFFF;")
        
        sep_h = QFrame(body)
        sep_h.setGeometry(0, self.SECTION_H, self.W, self.GRID_T)
        sep_h.setStyleSheet("background-color: #FFFFFF;")

    def _section_header(self, parent, text, w):
        lbl = QLabel(text, parent)
        lbl.setGeometry(0, 0, w, self.SECTION_H)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Times New Roman", 14, QFont.Bold))

    def _labeled_input(self, parent, text, x, y, col_w):
        lbl = QLabel(text, parent)
        lbl.setGeometry(x, y, 105, 36)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setFont(QFont("Times New Roman", 14, QFont.Bold))

        inp = QLineEdit(parent)
        inp.setGeometry(x + 117, y, col_w - x - 135, 36)
        inp.setStyleSheet("background-color: white; border: none; padding-left: 10px;")
        inp.setFont(QFont("Times New Roman", 14))
        return inp

    def _set_status(self, ok: bool, assigned: bool):
        self.status_text.setText("Оператор определен" if ok else "Оператор не определен")
        self.status_icon.setPixmap(_make_icon(ok))
        
        color = "#13FA23" if ok else "#FA1313"
        self.id_banner.setStyleSheet(f"background-color: {color};")
        
        hint = 'Для запуска программы\nнажмите "Далее"' if ok else "Запуск программы\nневозможен"
        self.info_hint.setText(hint)
        self.btn_next.setEnabled(ok)
        
        if assigned and self.current_id:
            self.id_banner.setText(f"ID {_id_str(self.current_id)}")
        else:
            self.id_banner.setText("ID не присвоен")

    def _validate_fields(self):
        ln = self.in_last.text().strip()
        fn = self.in_first.text().strip()
        mn = self.in_middle.text().strip()
        age = self.in_age.text().strip()
        
        name_re = re.compile(r"^[A-Za-zА-Яа-яЁё \-]{1,50}$")
        
        if not ln or not fn:
            return None, "Фамилия и Имя обязательны."
            
        if not name_re.match(ln) or not name_re.match(fn):
            return None, "ФИО: только буквы, пробел, дефис."
            
        if mn and not name_re.match(mn):
            return None, "ФИО: только буквы, пробел, дефис."
            
        if not age.isdigit() or int(age) < 18: 
            return None, "Возраст должен быть числом не менее 18 лет."
            
        data = {
            "last_name": ln, 
            "first_name": fn, 
            "middle_name": mn, 
            "age": age
        }
        return data, None

    def _append_csv_row(self, operator):
        new_id = _next_id(self.csv_file)
        with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                str(new_id), 
                _safe_csv_cell(operator["last_name"]), 
                _safe_csv_cell(operator["first_name"]),
                _safe_csv_cell(operator["middle_name"]), 
                operator["age"], 
                _now_date_str(),
                _now_time_str(), 
                self.software_start_time, 
                "00:00:00"
            ])
        return new_id

    def _start_camera(self):
        self.cap = cv2.VideoCapture(0)
        self.timer.start(30)

    def _stop_camera(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
        self.cap = None
        
        default_pix = QPixmap("assets/face.png")
        self.cam_view.setPixmap(
            default_pix.scaled(self.cam_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _grab_frame(self):
        if not self.cap:
            return
        ok, frame = self.cap.read()
        if ok and frame is not None:
            self.last_frame = cv2.flip(frame, 1)
            _draw_to_label_with_dpr(self.last_frame, self.cam_view)

    def _on_identify_clicked(self):
        self._start_camera()
        self._set_status(False, assigned=True)
        QTimer.singleShot(1200, self._try_verify)

    def _try_verify(self):
        if self.last_frame is None or self.current_id is None:
            self._set_status(False, assigned=self.current_id is not None)
            return

        live_face_gray, live_loc = get_cv_face(self.last_frame)
        
        if not self._known_enc_cache:
            self._known_enc_cache = cv_load_known_faces(self.ops_dir, exclude_id=self.current_id)

        is_invalid = live_face_gray is None
        is_duplicate = cv_find_match(self._known_enc_cache, live_face_gray) is not None
        
        if is_invalid or is_duplicate:
            self._set_status(False, assigned=True)
            res = QMessageBox.question(
                self, "Идентификация", "Пройти идентификацию заново?", 
                QMessageBox.Yes | QMessageBox.No
            )
            if res == QMessageBox.Yes:
                QTimer.singleShot(700, self._try_verify)
            else:
                self._stop_camera()
            return

        save_path = os.path.join(self.ops_dir, f"ID_{_id_str(self.current_id)}.jpg")
        _opencv_save_jpg(self.last_frame, save_path, face_loc=live_loc)
        self._set_status(True, assigned=True)

    def _on_save(self):
        if self.current_id is None:
            operator, err = self._validate_fields()
            if err:
                QMessageBox.warning(self, "Проверка данных", err)
                return
            self.current_id = self._append_csv_row(operator)
            self._known_enc_cache = None

        self.btn_identify.setEnabled(True)
        QMessageBox.information(self, "Успех", "Данные сохранены. Нажмите «Идентификация».")

    def _go_start(self):
        self._stop_camera()
        if self.start_screen:
            self.start_screen.show()
        self.hide()

    def closeEvent(self, event):
        self._stop_camera()
        if self.start_screen:
            self.start_screen.show()
        super().closeEvent(event)