import os
import re
import csv
import cv2
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QLineEdit, QFrame, QMessageBox, QWidget, QLabel, QPushButton,
)

from utils import (
    OPENCV_FACE_OK, _make_icon, _id_str,
    _next_id, _safe_csv_cell, _now_date_str, _now_time_str,
    _draw_to_label_with_dpr, _opencv_save_jpg,
    get_cv_face, cv_find_match, cv_load_known_faces
)


class RegistrationForm(QWidget):
    def __init__(self, start_screen, csv_file: str, ops_dir: str, software_start_time: str):
        super().__init__()
        self.start_screen = start_screen
        self.csv_file = csv_file
        self.ops_dir = ops_dir
        self.software_start_time = software_start_time

        self.current_id = None

        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._grab_frame)
        self.last_frame = None

        self._known_enc_cache = None

        self.W = 1000
        self.H = 450
        self.HEADER_H = 120
        self.BODY_H = self.H - self.HEADER_H
        self.SECTION_H = 44
        self.GRID_T = 4

        self.setFixedSize(self.W, self.H)
        self.setWindowTitle("НейроБодр")
        self.setStyleSheet("background-color: #D9D9D9;")

        self._build_ui()
        self._set_status(False, assigned=False)


    def reset_form(self):
        self.current_id = None
        
        self.in_last.clear()
        self.in_first.clear()
        self.in_middle.clear()
        self.in_age.clear()
        
        self._set_status(False, assigned=False)
        self.btn_next.setEnabled(False)
        self.btn_identify.setEnabled(False)
        
        self._known_enc_cache = None
        
        self.last_frame = None
        self.cam_view.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), "assets", "face.png")).scaled(self.cam_view.width(), self.cam_view.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _build_ui(self):
        header = QFrame(self)
        header.setGeometry(0, 0, self.W, self.HEADER_H)
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
        header_bottom.setGeometry(0, self.HEADER_H - self.GRID_T, self.W, self.GRID_T)
        header_bottom.setStyleSheet("background-color: #FFFFFF; border: none;")
        header_bottom.raise_()

        body = QFrame(self)
        body.setGeometry(0, self.HEADER_H, self.W, self.BODY_H)
        body.setStyleSheet("background-color: #D9D9D9; border: none;")

        col_w = self.W // 3
        col3_w = self.W - col_w * 2

        self.left = QFrame(body)
        self.left.setGeometry(0, 0, col_w, self.BODY_H)
        self.left.setStyleSheet("background-color: #D9D9D9; border: none;")

        self.mid = QFrame(body)
        self.mid.setGeometry(col_w, 0, col_w, self.BODY_H)
        self.mid.setStyleSheet("background-color: #D9D9D9; border: none;")

        self.right = QFrame(body)
        self.right.setGeometry(col_w * 2, 0, col3_w, self.BODY_H)
        self.right.setStyleSheet("background-color: #D9D9D9; border: none;")

        self._section_header(self.left, "Регистрация оператора", col_w)
        btn_w = 200
        btn_h = 35
        btn_x = int((col_w - btn_w) / 2)
        btn_y = int((self.SECTION_H - btn_h) / 2)
        
        self.btn_identify = QPushButton("Идентификация", self.mid)
        self.btn_identify.setGeometry(btn_x, btn_y, btn_w, btn_h)
        self.btn_identify.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2C; 
                color: #FFFFFF; 
                border: none;
                border-radius: 6px; 
                font-family: 'Times New Roman'; 
                font-size: 16px; 
            }
            QPushButton:hover { background-color: #44CC29; }
            QPushButton:disabled { background-color: #BDBDBD; color: #6B6B6B; }
        """)
        self.btn_identify.clicked.connect(self._on_identify_clicked)
        self.btn_identify.setEnabled(False)
        self._section_header(self.right, "Информационный блок", col3_w)

        field_step = 48
        y0 = self.SECTION_H + 30

        self.in_last = self._labeled_input(self.left, "Фамилия", 18, y0, col_w)
        self.in_first = self._labeled_input(self.left, "Имя", 18, y0 + field_step, col_w)
        self.in_middle = self._labeled_input(self.left, "Отчество", 18, y0 + field_step * 2, col_w)
        self.in_age = self._labeled_input(self.left, "Возраст", 18, y0 + field_step * 3, col_w)

        btn_y_level = y0 + field_step * 3 + 36 + 25

        self.btn_save = QPushButton("Записать", self.left)
        self.btn_save.setGeometry(col_w - 18 - 120, btn_y_level, 120, 34)
        self.btn_save.setCursor(Qt.PointingHandCursor)
        self.btn_save.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2C; color: #FFFFFF; border: none;
                border-radius: 6px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background-color: #44CC29; }
            QPushButton:pressed { background-color: #1F1F1F; }
        """)
        self.btn_save.clicked.connect(self._on_save)

        cam_w = col_w - 25
        cam_h = 220
        avail_h = self.BODY_H - self.SECTION_H
        cam_x = (col_w - cam_w) // 2
        cam_y = self.SECTION_H + (avail_h - cam_h) // 2

        self.cam_view = QLabel(self.mid)
        self.cam_view.setGeometry(cam_x, cam_y, cam_w, cam_h)
        self.cam_view.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), "assets", "face.png")).scaled(cam_w, cam_h, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        self.cam_view.setAlignment(Qt.AlignCenter)

        right_content_margin = 30
        right_content_width = col3_w - right_content_margin * 2

        self.status_row = QFrame(self.right)
        self.status_row.setGeometry(right_content_margin, y0, right_content_width, 36)
        self.status_row.setStyleSheet("background: transparent; border: none;")

        self.status_text = QLabel(self.status_row)
        self.status_text.setGeometry(0, 0, right_content_width - 34, 36)
        self.status_text.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.status_text.setStyleSheet("color: black; background: transparent;")
        self.status_text.setFont(QFont("Times New Roman", 14, QFont.Normal))

        self.status_icon = QLabel(self.status_row)
        self.status_icon.setGeometry(right_content_width - 28, 4, 28, 28)
        self.status_icon.setStyleSheet("background: transparent;")

        self.id_banner = QLabel(self.right)
        self.id_banner.setGeometry(right_content_margin, y0 + 60, right_content_width, 46)
        self.id_banner.setAlignment(Qt.AlignCenter)
        self.id_banner.setFont(QFont("Times New Roman", 18, QFont.Bold))

        self.info_hint = QLabel(self.right)
        self.info_hint.setGeometry(right_content_margin, y0 + 120, right_content_width, 60)
        self.info_hint.setWordWrap(True)
        self.info_hint.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.info_hint.setStyleSheet("color: black; background: transparent;")
        self.info_hint.setFont(QFont("Times New Roman", 14, QFont.Normal))

        self.btn_next = QPushButton("Далее", self.right)
        self.btn_next.setGeometry(col3_w - right_content_margin - 100, btn_y_level, 100, 34)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2C; color: #FFFFFF; border: none;
                border-radius: 6px; font-size: 12px; font-weight: 600;
            }
            QPushButton:hover { background-color: #44CC29; }
            QPushButton:disabled { background-color: #BDBDBD; color: #6B6B6B; }
        """)
        self.btn_next.setEnabled(False)
        self.btn_next.clicked.connect(self._go_start)

        self._grid(body, col_w)

    def _grid(self, body: QFrame, col_w: int):
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

    def _labeled_input(self, parent: QWidget, label: str, x: int, y: int, col_w: int) -> QLineEdit:
        lbl_w = 105
        lbl = QLabel(label, parent)
        lbl.setGeometry(x, y, lbl_w, 36)
        lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lbl.setStyleSheet("color: black; background: transparent; border: none;")
        lbl.setFont(QFont("Times New Roman", 14, QFont.Bold))

        inp = QLineEdit(parent)
        inp.setGeometry(x + lbl_w + 12, y, col_w - (x + lbl_w + 24) - 18, 36)
        inp.setFont(QFont("Times New Roman", 14))
        inp.setStyleSheet("""
            QLineEdit {
                background-color: white;
                border: none;
                padding-left: 10px;
            }
        """)
        return inp

    def _set_status(self, ok: bool, assigned: bool):
        if ok:
            self.status_text.setText("Оператор определен")
            self.status_icon.setPixmap(_make_icon(True))
            self.id_banner.setStyleSheet("background-color: #13FA23; color: black; border: none;")
            self.info_hint.setText('Для запуска программы\nнажмите "Далее"')
            self.btn_next.setEnabled(True)
        else:
            self.status_text.setText("Оператор не определен")
            self.status_icon.setPixmap(_make_icon(False))
            self.id_banner.setStyleSheet("background-color: #FA1313; color: black; border: none;")
            self.info_hint.setText("Запуск программы\nневозможен")
            self.btn_next.setEnabled(False)

        if assigned and self.current_id is not None:
            self.id_banner.setText(f"ID {_id_str(self.current_id)}")
        else:
            self.id_banner.setText("ID не присвоен")

    def _validate_fields(self):
        last_name = self.in_last.text().strip()
        first_name = self.in_first.text().strip()
        middle_name = self.in_middle.text().strip()
        age_s = self.in_age.text().strip()

        name_re = re.compile(r"^[A-Za-zА-Яа-яЁё \-]{1,50}$")

        if not last_name or not first_name:
            return None, "Фамилия и Имя обязательны."
        if not name_re.match(last_name) or not name_re.match(first_name):
            return None, "Фамилия/Имя: только буквы, пробел, дефис."
        if middle_name and not name_re.match(middle_name):
            return None, "Отчество: только буквы, пробел, дефис."

        if not age_s.isdigit():
            return None, "Возраст должен быть числом."
        age = int(age_s)
        if age < 18:
            return None, "Возраст должен быть не менее 18 лет."

        return {
            "last_name": last_name,
            "first_name": first_name,
            "middle_name": middle_name,
            "age": str(age)
        }, None

    def _append_csv_row(self, operator: dict) -> int:
        new_id = _next_id(self.csv_file)
        with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow([
                str(new_id),
                _safe_csv_cell(operator["last_name"]),
                _safe_csv_cell(operator["first_name"]),
                _safe_csv_cell(operator["middle_name"]) if operator["middle_name"] else "",
                operator["age"],
                _now_date_str(),
                _now_time_str(),
                self.software_start_time,
                "00:00:00"
            ])
        return new_id

    def _start_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0)

        if not self.cap.isOpened():
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
            QMessageBox.critical(self, "Камера", "Не удалось открыть камеру.")
            return False

        self.timer.start(30)
        return True

    def _stop_camera(self):
        self.timer.stop()
        if self.cap is not None:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        
        self.cam_view.setPixmap(QPixmap(os.path.join(os.path.dirname(__file__), "assets", "face.png")).scaled(self.cam_view.width(), self.cam_view.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _grab_frame(self):
        if self.cap is None:
            return

        ok, frame = self.cap.read()
        if not ok or frame is None:
            return
        
        frame = cv2.flip(frame, 1)

        self.last_frame = frame
        _draw_to_label_with_dpr(frame, self.cam_view)

    def _load_known_encodings_once(self):
        if self._known_enc_cache is None:
            self._known_enc_cache = cv_load_known_faces(self.ops_dir, exclude_id=self.current_id)
        return self._known_enc_cache

    def _on_identify_clicked(self):
        if not self._start_camera():
            return
        self._set_status(False, assigned=True)
        QTimer.singleShot(1200, self._try_verify)

    def _try_verify(self):
        if self.last_frame is None or self.current_id is None:
            self._set_status(False, assigned=self.current_id is not None)
            return

        if not OPENCV_FACE_OK:
            self._set_status(False, assigned=True)
            QMessageBox.critical(self, "Идентификация", "OpenCV распознавание недоступно.")
            return

        live_face_gray, live_loc = get_cv_face(self.last_frame)

        if live_face_gray is None:
            self._set_status(False, assigned=True)
            r = QMessageBox.question(self, "Идентификация", "Пройти идентификацию заново?",
                                    QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.Yes:
                QTimer.singleShot(700, self._try_verify)
            else:
                self._stop_camera()
            return

        known = self._load_known_encodings_once()
        match_id = cv_find_match(known, live_face_gray)
        
        if match_id is not None:
            self._set_status(False, assigned=True)
            r = QMessageBox.question(self, "Идентификация", "Пройти идентификацию заново?",
                                    QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.Yes:
                QTimer.singleShot(700, self._try_verify)
            else:
                self._stop_camera()
            return

        photo_path = os.path.join(self.ops_dir, f"ID_{_id_str(self.current_id)}.jpg")
        saved = _opencv_save_jpg(self.last_frame, photo_path, face_loc=live_loc)

        if not saved:
            QMessageBox.critical(self, "Ошибка", "Не удалось сохранить фото.")
            return

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
        QMessageBox.information(self, "Успех", "Данные сохранены. Теперь нажмите «Идентификация» для сканирования лица.")

    def _go_start(self):
        self._stop_camera()
        if self.start_screen is not None:
            self.start_screen.show()
        self.hide()

    def closeEvent(self, event):
        self._stop_camera()
        try:
            if self.start_screen is not None:
                self.start_screen.show()
        except Exception:
            pass
        super().closeEvent(event)