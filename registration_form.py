import os
import re
import csv
import cv2
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QFrame, QMessageBox, QWidget, QLabel, 
    QPushButton, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy
)

from utils import (
    make_icon, id_str, next_id, now_date_str, 
    now_time_str, draw_to_label_with_dpr, _opencv_save_jpg,
    get_cv_face, cv_find_match, cv_load_known_faces,
    BaseWindow, create_label, COLOR_BG, COLOR_GREEN, 
    COLOR_BTN_BG, COLOR_DISABLED, create_line_edit, getbtn_style, 
)

class RegistrationForm(BaseWindow):
    def __init__(self, start_screen, csv_file: str, ops_dir: str, software_start_time: str):
        super().__init__(1000, 484, "НейроБодр")
        
        self.start_screen = start_screen
        self.csv_file = csv_file
        self.ops_dir = ops_dir
        self.software_start_time = software_start_time

        self.current_id = None
        self.cap = None
        self._known_enc_cache = None
        self.last_frame = None
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.grab_frame)

        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.build_ui(content_layout)
        self.set_status(False, assigned=False)

    def reset_form(self):
        self.current_id = None
        self._known_enc_cache = None
        self.last_frame = None
        
        inputs = (self.in_last, self.in_first, self.in_middle, self.in_age)
        for inp in inputs:
            inp.clear()
        
        self.set_status(False, assigned=False)
        self.btn_next.setEnabled(False)
        
        default_pix = QPixmap("assets/face.png")
        if not default_pix.isNull():
            self.cam_view.setPixmap(
                default_pix.scaled(self.cam_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def build_ui(self, parent_layout):
        header = QFrame()
        header.setFixedHeight(120)
        header.setStyleSheet(f"background-color: {COLOR_GREEN};")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(0, 10, 0, 10)
        header_layout.setSpacing(5)

        t1 = create_label("НейроБодр", 40, bold=True, color="white", align=Qt.AlignCenter)
        header_layout.addWidget(t1)

        line_layout = QHBoxLayout()
        line_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet("background-color: white;")
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line_layout.addWidget(line, stretch=3) 
        line_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        header_layout.addLayout(line_layout)

        t2 = create_label("Программа для мониторинга состояния водителей", 16, color="white", align=Qt.AlignCenter)
        header_layout.addWidget(t2)

        parent_layout.addWidget(header)

        body_container = QWidget()
        body_container.setStyleSheet("background-color: white;")
        
        body_main_layout = QVBoxLayout(body_container)
        body_main_layout.setContentsMargins(0, 4, 0, 0)
        body_main_layout.setSpacing(4)

        top_row = QWidget()
        top_row.setFixedHeight(44)
        top_layout = QHBoxLayout(top_row)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(4)

        left_header = QFrame()
        left_header.setStyleSheet(f"background-color: {COLOR_BG};")
        mid_header = QFrame()
        mid_header.setStyleSheet(f"background-color: {COLOR_BG};")
        right_header = QFrame()
        right_header.setStyleSheet(f"background-color: {COLOR_BG};")

        top_layout.addWidget(left_header, stretch=1)
        top_layout.addWidget(mid_header, stretch=1)
        top_layout.addWidget(right_header, stretch=1)

        lh_layout = QVBoxLayout(left_header)
        lbl_reg = create_label("Регистрация оператора", 14, bold=True, align=Qt.AlignCenter)
        lh_layout.addWidget(lbl_reg)

        mh_layout = QHBoxLayout(mid_header)
        self.btn_identify = QPushButton("Идентификация")
        self.btn_identify.setFixedSize(200, 35)
        self.btn_identify.setCursor(Qt.PointingHandCursor)
        self.btn_identify.setStyleSheet(
            getbtn_style() + 
            f" QPushButton:disabled {{ background-color: {COLOR_DISABLED}; color: gray; }}"
        )
        self.btn_identify.clicked.connect(self.on_identify_clicked)
        mh_layout.addWidget(self.btn_identify, alignment=Qt.AlignCenter)

        rh_layout = QVBoxLayout(right_header)
        lbl_info = create_label("Информационный блок", 14, bold=True, align=Qt.AlignCenter)
        rh_layout.addWidget(lbl_info)

        body_main_layout.addWidget(top_row)

        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)

        self.left = QFrame()
        self.left.setStyleSheet(f"background-color: {COLOR_BG};")
        self.mid = QFrame()
        self.mid.setStyleSheet(f"background-color: {COLOR_BG};")
        self.right = QFrame()
        self.right.setStyleSheet(f"background-color: {COLOR_BG};")

        bottom_layout.addWidget(self.left, stretch=1)
        bottom_layout.addWidget(self.mid, stretch=1)
        bottom_layout.addWidget(self.right, stretch=1)

        body_main_layout.addWidget(bottom_row, stretch=1)
        parent_layout.addWidget(body_container, stretch=1)

        left_layout = QVBoxLayout(self.left)
        left_layout.setContentsMargins(15, 20, 15, 20)
        left_layout.setSpacing(10)

        self.in_last = self.add_labeled_input(left_layout, "Фамилия")
        self.in_first = self.add_labeled_input(left_layout, "Имя")
        self.in_middle = self.add_labeled_input(left_layout, "Отчество")
        self.in_age = self.add_labeled_input(left_layout, "Возраст")

        left_layout.addStretch()

        btn_save_layout = QHBoxLayout()
        btn_save_layout.addStretch()
        self.btn_save = self.createbtn("Записать", self.on_save, 120)
        btn_save_layout.addWidget(self.btn_save)
        left_layout.addLayout(btn_save_layout)

        mid_layout = QVBoxLayout(self.mid)
        mid_layout.setContentsMargins(15, 20, 15, 20)
        
        mid_layout.addStretch()
        self.cam_view = QLabel()
        self.cam_view.setFixedSize(300, 220)
        self.cam_view.setAlignment(Qt.AlignCenter)
        self.cam_view.setStyleSheet("background-color: white;") 
        
        cam_layout = QHBoxLayout()
        cam_layout.addStretch()
        cam_layout.addWidget(self.cam_view)
        cam_layout.addStretch()
        mid_layout.addLayout(cam_layout)
        mid_layout.addStretch()

        right_layout = QVBoxLayout(self.right)
        right_layout.setContentsMargins(15, 20, 15, 20)
        right_layout.setSpacing(10)

        status_layout = QHBoxLayout()
        self.status_text = create_label("", 14)
        
        self.status_icon = QLabel()
        self.status_icon.setFixedSize(28, 28)
        self.status_icon.setScaledContents(True)
        
        status_layout.addWidget(self.status_text)
        status_layout.addStretch()
        status_layout.addWidget(self.status_icon)
        right_layout.addLayout(status_layout)

        self.id_banner = create_label("", 18, bold=True, align=Qt.AlignCenter)
        self.id_banner.setFixedHeight(46)
        right_layout.addWidget(self.id_banner)

        self.info_hint = create_label("", 14)
        right_layout.addWidget(self.info_hint)

        right_layout.addStretch()

        btn_next_layout = QHBoxLayout()
        btn_next_layout.addStretch()
        self.btn_next = self.createbtn("Далее", self.go_start, 100)
        btn_next_layout.addWidget(self.btn_next)
        right_layout.addLayout(btn_next_layout)

    def createbtn(self, text, callback, width):
        btn = QPushButton(text)
        btn.setFixedSize(width, 34)
        btn.setCursor(Qt.PointingHandCursor)
        btn.setStyleSheet(
            getbtn_style() + 
            f" QPushButton:disabled {{ background-color: {COLOR_DISABLED}; color: gray; }}"
        )
        btn.clicked.connect(callback)
        return btn

    def add_labeled_input(self, parent_layout, text):
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)
        
        lbl = create_label(text, 14, bold=True, align=Qt.AlignRight | Qt.AlignVCenter)
        lbl.setFixedWidth(85)

        inp = create_line_edit(height=36, font_size=14, padding=10)

        row_layout.addWidget(lbl)
        row_layout.addWidget(inp)
        parent_layout.addLayout(row_layout)
        
        return inp

    def set_status(self, ok: bool, assigned: bool):
        self.status_text.setText("Оператор определен" if ok else "Оператор не определен")
        
        pixmap = make_icon(ok)
        if pixmap:
            self.status_icon.setPixmap(pixmap)
        
        color = COLOR_GREEN if ok else "red"
        self.id_banner.setStyleSheet(f"background-color: {color}; color: {COLOR_BTN_BG};")
        
        hint = 'Для запуска программы\nнажмите "Далее"' if ok else "Запуск программы\nневозможен"
        self.info_hint.setText(hint)
        self.btn_next.setEnabled(ok)
        
        if assigned and self.current_id:
            self.id_banner.setText(f"ID {id_str(self.current_id)}")
        else:
            self.id_banner.setText("ID не присвоен")

    def validate_fields(self):
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

def append_csv_row(self, operator):
        new_id = next_id(self.csv_file)
        with open(self.csv_file, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow([
                str(new_id), 
                operator["last_name"].strip(), 
                operator["first_name"].strip(),
                operator["middle_name"].strip(), 
                str(operator["age"]).strip(),
                now_date_str(),
                now_time_str(), 
                self.software_start_time, 
                "00:00:00"
            ])
        return new_id

    def start_camera(self):
        self.cap = cv2.VideoCapture(0)
        self.timer.start(30)

    def stop_camera(self):
        self.timer.stop()
        if self.cap:
            self.cap.release()
        self.cap = None
        
        default_pix = QPixmap("assets/face.png")
        if not default_pix.isNull():
            self.cam_view.setPixmap(
                default_pix.scaled(self.cam_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

    def grab_frame(self):
        if not self.cap:
            return
        ok, frame = self.cap.read()
        if ok and frame is not None:
            self.last_frame = cv2.flip(frame, 1)
            draw_to_label_with_dpr(self.last_frame, self.cam_view)

    def on_identify_clicked(self):
        self.start_camera()
        self.set_status(False, assigned=True)
        QTimer.singleShot(1200, self.try_verify)

    def try_verify(self):
        if self.last_frame is None:
            return

        if self.current_id is None:
            operator, err = self.validate_fields()
            if err:
                self.stop_camera()
                QMessageBox.warning(self, "Ошибка", f"Сначала заполните данные: {err}")
                return
            
            self.current_id = self.append_csv_row(operator)
            self._known_enc_cache = None

        live_face_gray, live_loc = get_cv_face(self.last_frame)
        
        if not self._known_enc_cache:
            self._known_enc_cache = cv_load_known_faces(self.ops_dir, exclude_id=self.current_id)

        is_invalid = live_face_gray is None
        is_duplicate = cv_find_match(self._known_enc_cache, live_face_gray) is not None
        
        if is_invalid or is_duplicate:
            self.set_status(False, assigned=True)
            res = QMessageBox.question(
                self, "Идентификация", "Пройти идентификацию заново?", 
                QMessageBox.Yes | QMessageBox.No
            )
            if res == QMessageBox.Yes:
                QTimer.singleShot(700, self.try_verify)
            else:
                self.stop_camera()
            return

        save_path = os.path.join(self.ops_dir, f"ID_{id_str(self.current_id)}.jpg")
        _opencv_save_jpg(self.last_frame, save_path, face_loc=live_loc)
        self.set_status(True, assigned=True)

    def on_save(self):
        if self.current_id is None:
            operator, err = self.validate_fields()
            if err:
                QMessageBox.warning(self, "Проверка данных", err)
                return
            self.current_id = self.append_csv_row(operator)
            self._known_enc_cache = None

        QMessageBox.information(self, "Успех", "Данные сохранены. Нажмите «Идентификация».")

    def go_start(self):
        self.stop_camera()
        if self.start_screen:
            self.start_screen.show()
        self.hide()

    def closeEvent(self, event):
        self.stop_camera()
        if self.start_screen:
            self.start_screen.show()
        super().closeEvent(event)