import os
from datetime import datetime
import cv2
from PyQt5.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QMessageBox, QVBoxLayout, QHBoxLayout
)

from instruction_form import InstructionForm

from utils import (
    OPENCV_FACE_OK, _make_icon, _parse_hms_to_seconds,
    _seconds_to_hms, _id_str, _draw_to_label_with_dpr,
    get_cv_face, cv_compare_faces, _opencv_imread_unicode
)


class FaceWorker(QObject):
    finished = pyqtSignal(bool, object)

    @pyqtSlot(object, object)
    def process_frame(self, frame, ref_face_gray):
        try:
            live_face_gray, loc = get_cv_face(frame)
            if live_face_gray is None:
                self.finished.emit(False, None)
                return

            is_same = cv_compare_faces(ref_face_gray, live_face_gray)
            self.finished.emit(is_same, loc)
        except Exception:
            self.finished.emit(False, None)

class InfoForm(QWidget):
    sig_process = pyqtSignal(object, object)

    def __init__(self, start_screen, auth_screen, operator_row: dict, csv_file: str, ops_dir: str):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.start_screen = start_screen
        self.auth_screen = auth_screen
        self.csv_file = csv_file
        self.ops_dir = ops_dir

        self.operator_row = operator_row
        self.op_id = int(str(operator_row.get("id", "0")).strip() or "0")

        self.face_thread = QThread()
        self.worker = FaceWorker()
        self.worker.moveToThread(self.face_thread)

        self.sig_process.connect(self.worker.process_frame)
        self.worker.finished.connect(self._on_verification_result)
        self.face_thread.start()

        self.is_processing = False
        self.last_face_loc = None
        self.last_face_ok = False

        self.cap = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._grab_frame)
        self.last_frame = None

        self.presence_timer = QTimer(self)
        self.presence_timer.timeout.connect(self._check_presence)
        self.presence_timer.setInterval(1000)

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        self.is_verified = False
        self.is_present = False
        self._ref_enc_cache = None

        self.W = 1000
        self.H = 450
        self.HEADER_H = 120
        self.BODY_H = self.H - self.HEADER_H
        self.SECTION_H = 44
        self.GRID_T = 4

        self.setFixedSize(self.W, self.H + 34)
        self.setWindowTitle("Информация оператора")
        self.setStyleSheet("background-color: #D9D9D9;")

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.top_grey_area = QWidget(self)
        self.top_grey_area.setFixedHeight(30)
        self.top_grey_area.setStyleSheet("background-color: #D9D9D9; border: none;")
        
        top_layout = QHBoxLayout(self.top_grey_area)
        top_layout.setContentsMargins(0, 0, 5, 0)
        top_layout.setSpacing(0)
        top_layout.addStretch(1)

        self.btn_close = QPushButton("×", self.top_grey_area)
        self.btn_close.setFixedSize(45, 30)
        self.btn_close.setCursor(Qt.PointingHandCursor)
        self.btn_close.setStyleSheet("""
            QPushButton {
                color: #FF0000; 
                background: transparent; 
                border: none; 
                font-size: 36px; 
                font-weight: bold;
            }
        """)
        self.btn_close.clicked.connect(self.close)
        top_layout.addWidget(self.btn_close)
        main_layout.addWidget(self.top_grey_area)

        self.top_white_line = QWidget(self)
        self.top_white_line.setFixedHeight(4)
        self.top_white_line.setStyleSheet("background-color: #FFFFFF; border: none;")
        main_layout.addWidget(self.top_white_line)

        self.content_container = QWidget(self)
        self.content_container.setFixedSize(self.W, self.H)
        main_layout.addWidget(self.content_container)

        self._build_ui()
        self._reset_state()
        self._update_status()

        if not OPENCV_FACE_OK:
            QMessageBox.warning(self, "Зависимость", "Модуль распознавания OpenCV не настроен.")

        if self._start_camera():
            QTimer.singleShot(1200, self._try_verify)

    def _update_clock(self):
        now_dt = datetime.now().strftime("%d.%m.%Y / %H:%M:%S")
        self.lbl_dt.setText(f"Дата/время: <b>{now_dt}</b>")

    def set_operator_row(self, operator_row: dict):
        self.operator_row = operator_row
        self.op_id = int(str(operator_row.get("id", "0")).strip() or "0")
        self._ref_enc_cache = None
        self._reset_state()
        self._refresh_left_info()
        self._update_status()
        self._stop_camera()
        if self._start_camera():
            QTimer.singleShot(1200, self._try_verify)

    def _reset_state(self):
        self.is_verified = False
        self.is_present = False
        self.is_processing = False
        if hasattr(self, 'presence_timer'):
            self.presence_timer.stop()

    def _build_ui(self):
        header = QFrame(self.content_container)
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

        header_bottom = QFrame(self.content_container)
        header_bottom.setGeometry(0, self.HEADER_H - self.GRID_T, self.W, self.GRID_T)
        header_bottom.setStyleSheet("background-color: #FFFFFF; border: none;")
        header_bottom.raise_()

        body = QFrame(self.content_container)
        body.setGeometry(0, self.HEADER_H, self.W, self.BODY_H)
        body.setStyleSheet("background-color: #D9D9D9; border: none;")

        col_w = self.W // 3
        col3_w = self.W - col_w * 2

        self.left = QFrame(body)
        self.left.setGeometry(0, 0, col_w, self.BODY_H)
        self.mid = QFrame(body)
        self.mid.setGeometry(col_w, 0, col_w, self.BODY_H)
        self.right = QFrame(body)
        self.right.setGeometry(col_w * 2, 0, col3_w, self.BODY_H)

        self._section_header(self.left, "Информация оператора", col_w)
        btn_w = 200
        btn_h = 35
        btn_x = int((col_w - btn_w) / 2)
        btn_y = int((self.SECTION_H - btn_h) / 2)

        self.btn_identify_dummy = QPushButton("Идентификация", self.mid)
        self.btn_identify_dummy.setGeometry(btn_x, btn_y, btn_w, btn_h)
        self.btn_identify_dummy.setStyleSheet("""
            QPushButton {
                background-color: #2C2C2C; 
                color: #FFFFFF; 
                border: none;
                border-radius: 6px; 
                font-family: 'Times New Roman'; 
                font-size: 16px; 
            }
        """)
        self._section_header(self.right, "Информационный блок", col3_w)

        self._build_left_info(col_w)

        cam_w, cam_h = col_w - 30, 220
        cam_x = (col_w - cam_w) // 2
        cam_y = self.SECTION_H + (self.BODY_H - self.SECTION_H - cam_h) // 2
        self.cam_view = QLabel(self.mid)
        self.cam_view.setGeometry(cam_x, cam_y, cam_w, cam_h)
        self.cam_view.setStyleSheet("background-color: white; border: none;")
        self.cam_view.setAlignment(Qt.AlignCenter)

        y0 = self.SECTION_H + 30
        right_m = 30
        right_w = col3_w - right_m * 2
        self.status_row = QFrame(self.right)
        self.status_row.setGeometry(right_m, y0, right_w, 36)
        self.status_text = QLabel(self.status_row)
        self.status_text.setGeometry(0, 0, right_w - 34, 36)
        self.status_text.setFont(QFont("Times New Roman", 14))
        self.status_icon = QLabel(self.status_row)
        self.status_icon.setGeometry(right_w - 28, 4, 28, 28)

        self.id_banner = QLabel(self.right)
        self.id_banner.setGeometry(right_m, y0 + 60, right_w, 46)
        self.id_banner.setAlignment(Qt.AlignCenter)
        self.id_banner.setFont(QFont("Times New Roman", 18, QFont.Bold))

        self.info_hint = QLabel(self.right)
        self.info_hint.setGeometry(right_m, y0 + 120, right_w, 60)
        self.info_hint.setWordWrap(True)
        self.info_hint.setFont(QFont("Times New Roman", 14))

        self.btn_next = QPushButton("Далее", self.right)
        self.btn_next.setGeometry(col3_w - right_m - 100, self.SECTION_H + 203, 100, 34)
        self.btn_next.setStyleSheet("""
            QPushButton { background-color: #2C2C2C; color: white; border-radius: 6px; } 
            QPushButton:hover { background-color: #44CC29; }
            QPushButton:disabled { background-color: #BDBDBD; }
        """)
        self.btn_next.clicked.connect(self._finish)

        sep1 = QFrame(body)
        sep1.setGeometry(col_w - 2, 0, 4, self.BODY_H)
        sep1.setStyleSheet("background: white")
        sep2 = QFrame(body)
        sep2.setGeometry(col_w * 2 - 2, 0, 4, self.BODY_H)
        sep2.setStyleSheet("background: white")
        sep_h = QFrame(body)
        sep_h.setGeometry(0, self.SECTION_H, self.W, 4)
        sep_h.setStyleSheet("background: white")
        sep1.raise_()
        sep2.raise_()
        sep_h.raise_()

    def _section_header(self, parent, text, width):
        h = QFrame(parent)
        h.setGeometry(0, 0, width, self.SECTION_H)
        lbl = QLabel(text, h)
        lbl.setGeometry(0, 0, width, self.SECTION_H)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Times New Roman", 14, QFont.Bold))

    def _build_left_info(self, col_w):
        y = self.SECTION_H + 20
        self.photo = QLabel(self.left)
        self.photo.setGeometry(10, y, 90, 100)
        self.lbl_name = QLabel(self.left)
        self.lbl_name.setGeometry(118, y + 10, col_w - 136, 60)
        self.lbl_name.setWordWrap(True)
        self.lbl_name.setFont(QFont("Times New Roman", 18))
        self.lbl_age = QLabel(self.left)
        self.lbl_age.setGeometry(118, y + 65, col_w - 136, 28)
        self.lbl_age.setFont(QFont("Times New Roman", 18))

        y2 = y + 115
        self.lbl_dt = QLabel(self.left)
        self.lbl_dt.setGeometry(18, y2, col_w - 36, 26)
        self.lbl_start = QLabel(self.left)
        self.lbl_start.setGeometry(18, y2 + 30, col_w - 36, 26)
        self.lbl_drive = QLabel(self.left)
        self.lbl_drive.setGeometry(18, y2 + 60, col_w - 36, 26)
        self.lbl_left = QLabel(self.left)
        self.lbl_left.setGeometry(18, y2 + 90, col_w - 36, 26)
        self._refresh_left_info()

    def _refresh_left_info(self):
        row = self.operator_row or {}
        fio = " ".join(filter(None, [row.get("last_name"), row.get("first_name"), row.get("middle_name")]))
        self.lbl_name.setText(fio or "—")
        self.lbl_age.setText(f"{row.get('age', '')} лет" if row.get('age') else "—")
        sw_start = (row.get("software_start_time") or "").strip()
        self.lbl_start.setText(f"Время запуска ПО: <b>{sw_start or '—'}</b>")
        drive = (row.get("drive_duration") or "00:00:00").strip()
        self.lbl_drive.setText(f"Время в дороге: <b>{drive}</b>")
        left_sec = 9 * 3600 - _parse_hms_to_seconds(drive)
        self.lbl_left.setText(f"Оставшееся время: <b>{_seconds_to_hms(left_sec)}</b>")

        photo_path = os.path.join(self.ops_dir, f"ID_{_id_str(self.op_id)}.jpg")
        if os.path.exists(photo_path):
            pm = QPixmap(photo_path)
            self.photo.setPixmap(pm.scaled(90, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def _update_status(self):
        if self.is_verified and self.is_present:
            self.status_text.setText("Оператор определен")
            self.status_icon.setPixmap(_make_icon(True))
            self.id_banner.setStyleSheet("background-color: #13FA23; color: black;")
            self.id_banner.setText(f"ID {_id_str(self.op_id)}")
            self.info_hint.setText('Для запуска программы\nнажмите "Далее"')
            self.btn_next.setEnabled(True)
        else:
            self.status_text.setText("Оператор не определен")
            self.status_icon.setPixmap(_make_icon(False))
            self.id_banner.setStyleSheet("background-color: #FA1313; color: black;")
            self.id_banner.setText("ID не определен")
            self.info_hint.setText("Запуск программы\nневозможен")
            self.btn_next.setEnabled(False)

    def _start_camera(self):
        if self.cap is None:
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW if hasattr(cv2, "CAP_DSHOW") else 0)
        if not self.cap.isOpened():
            self.cap = None
            QMessageBox.critical(self, "Камера", "Не удалось открыть камеру.")
            return False
        self.timer.start(30)
        return True

    def _stop_camera(self):
        self.timer.stop()
        self.presence_timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None

    def _grab_frame(self):
        if self.cap is None: return
        ok, frame = self.cap.read()
        if ok and frame is not None:
            frame = cv2.flip(frame, 1)
            self.last_frame = frame.copy()
            
            if self.last_face_loc:
                y, right, b, x = self.last_face_loc
                color = (0, 255, 0) if self.last_face_ok else (0, 0, 255)
                cv2.rectangle(frame, (x, y), (right, b), color, 2)
                
            _draw_to_label_with_dpr(frame, self.cam_view)

    def _get_reference_encoding_cached(self):
        if self._ref_enc_cache is not None: 
            return self._ref_enc_cache
        
        ref_path = os.path.join(self.ops_dir, f"ID_{_id_str(self.op_id)}.jpg")
        ref_img = _opencv_imread_unicode(ref_path)
        
        if ref_img is None:
            return None
            
        face_gray, _ = get_cv_face(ref_img)
        self._ref_enc_cache = face_gray
        return self._ref_enc_cache

    def _check_presence(self):
        if not self.is_verified or self.last_frame is None or self.is_processing:
            return

        ref_enc = self._get_reference_encoding_cached()
        if ref_enc is not None:
            self.is_processing = True
            self.sig_process.emit(self.last_frame.copy(), ref_enc)

    def _on_verification_result(self, is_same_person, loc):
        self.is_processing = False
        self.is_present = is_same_person
        self.last_face_loc = loc
        self.last_face_ok = is_same_person
        self._update_status()

    def _try_verify(self):
        if self.last_frame is None:
            QTimer.singleShot(500, self._try_verify)
            return

        ref_face_gray = self._get_reference_encoding_cached()
        if ref_face_gray is None:
            QMessageBox.critical(self, "Ошибка", "Эталонное лицо не найдено в файле.")
            return

        live_face_gray, loc = get_cv_face(self.last_frame)
        
        if loc is None:
            self.last_face_loc = None
            self.last_face_ok = False
            
            _draw_to_label_with_dpr(self.last_frame, self.cam_view)
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()

            r = QMessageBox.question(self, "Идентификация", "Пройти идентификацию заново?", QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.Yes: QTimer.singleShot(700, self._try_verify)
            return

        self.is_verified = cv_compare_faces(ref_face_gray, live_face_gray)
        self.last_face_loc = loc
        self.last_face_ok = self.is_verified
        
        frame_draw = self.last_frame.copy()
        y, right, b, x = loc
        color = (0, 255, 0) if self.is_verified else (0, 0, 255)
        cv2.rectangle(frame_draw, (x, y), (right, b), color, 2)
        _draw_to_label_with_dpr(frame_draw, self.cam_view)
        from PyQt5.QtWidgets import QApplication
        QApplication.processEvents()

        if self.is_verified:
            self.is_present = True
            self.presence_timer.start()
            self._update_status()
        else:
            r = QMessageBox.question(self, "Идентификация", "Пройти идентификацию заново?",
                                    QMessageBox.Yes | QMessageBox.No)
            if r == QMessageBox.Yes: QTimer.singleShot(700, self._try_verify)

    def _finish(self):
        self._stop_camera()

        if self.face_thread.isRunning():
            self.face_thread.quit()
            self.face_thread.wait()

        self.instr_form = InstructionForm(self.operator_row)
        self.instr_form.show()

        self.hide()

    def closeEvent(self, event):
        self._stop_camera()
        if self.face_thread.isRunning():
            self.face_thread.quit()
            self.face_thread.wait()
        if self.auth_screen: self.auth_screen.show()
        super().closeEvent(event)