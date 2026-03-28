import os
from datetime import datetime
import cv2
from PyQt5.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont, QPixmap
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QMessageBox, 
    QVBoxLayout, QHBoxLayout, QApplication
)

from instruction_form import InstructionForm
from utils import (
    _make_icon, _parse_hms_to_seconds, _seconds_to_hms, 
    _id_str, _draw_to_label_with_dpr, get_cv_face, 
    cv_compare_faces, _opencv_imread_unicode
)


class FaceWorker(QObject):
    finished = pyqtSignal(bool, object)

    @pyqtSlot(object, object)
    def process_frame(self, frame, ref_face_gray):
        live_face_gray, loc = get_cv_face(frame)
        
        if live_face_gray is None:
            self.finished.emit(False, None)
            return
            
        is_same = cv_compare_faces(ref_face_gray, live_face_gray)
        self.finished.emit(is_same, loc)


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
        
        id_raw = str(operator_row.get("id", "0")).strip()
        if not id_raw:
            id_raw = "0"
        self.op_id = int(id_raw)

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
        self.last_frame = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._grab_frame)
        
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
        self.SECTION_H = 44
        self.GRID_T = 4
        self.BODY_H = self.H - self.HEADER_H

        self.setFixedSize(self.W, self.H + 34)
        self.setWindowTitle("Информация оператора")
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
        self._reset_state()
        self._update_status()

        if self._start_camera():
            QTimer.singleShot(1200, self._try_verify)

    def _update_clock(self):
        now_str = datetime.now().strftime('%d.%m.%Y / %H:%M:%S')
        self.lbl_dt.setText(f"Дата/время: <b>{now_str}</b>")

    def set_operator_row(self, operator_row: dict):
        self.operator_row = operator_row
        
        id_raw = str(operator_row.get("id", "0")).strip()
        if not id_raw:
            id_raw = "0"
        self.op_id = int(id_raw)
        
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

        self._section_header(self.left, "Информация оператора", col_w)
        self._section_header(self.right, "Информационный блок", col3_w)

        self.btn_identify_dummy = QPushButton("Идентификация", self.mid)
        btn_x = (col_w - 200) // 2
        btn_y = (self.SECTION_H - 35) // 2
        self.btn_identify_dummy.setGeometry(btn_x, btn_y, 200, 35)
        self.btn_identify_dummy.setStyleSheet(
            "background-color: #2C2C2C; color: #FFFFFF; "
            "border-radius: 6px; font-size: 16px;"
        )

        self._build_left_info(col_w)

        cam_w = col_w - 30
        cam_h = 220
        cam_x = (col_w - cam_w) // 2
        cam_y = self.SECTION_H + (self.BODY_H - self.SECTION_H - cam_h) // 2
        
        self.cam_view = QLabel(self.mid)
        self.cam_view.setGeometry(cam_x, cam_y, cam_w, cam_h)
        self.cam_view.setStyleSheet("background-color: white;")
        self.cam_view.setAlignment(Qt.AlignCenter)

        right_w = col3_w - 60
        y0 = self.SECTION_H + 30
        
        self.status_text = QLabel(self.right)
        self.status_text.setGeometry(30, y0, right_w - 34, 36)
        self.status_text.setFont(QFont("Times New Roman", 14))
        
        self.status_icon = QLabel(self.right)
        self.status_icon.setGeometry(30 + right_w - 28, y0 + 4, 28, 28)

        self.id_banner = QLabel(self.right)
        self.id_banner.setGeometry(30, y0 + 60, right_w, 46)
        self.id_banner.setFont(QFont("Times New Roman", 18, QFont.Bold))
        self.id_banner.setAlignment(Qt.AlignCenter)

        self.info_hint = QLabel(self.right)
        self.info_hint.setGeometry(30, y0 + 120, right_w, 60)
        self.info_hint.setFont(QFont("Times New Roman", 14))

        self.btn_next = QPushButton("Далее", self.right)
        self.btn_next.setGeometry(col3_w - 130, self.SECTION_H + 203, 100, 34)
        self.btn_next.setStyleSheet("""
            QPushButton { 
                background-color: #2C2C2C; 
                color: white; 
                border-radius: 6px; 
            } 
            QPushButton:hover { background-color: #44CC29; } 
            QPushButton:disabled { background-color: #BDBDBD; }
        """)
        self.btn_next.clicked.connect(self._finish)

        for x in (col_w, col_w * 2):
            sep = QFrame(body)
            sep.setGeometry(x - 2, 0, 4, self.BODY_H)
            sep.setStyleSheet("background: white")
        
        sep_h = QFrame(body)
        sep_h.setGeometry(0, self.SECTION_H, self.W, 4)
        sep_h.setStyleSheet("background: white")

    def _section_header(self, parent, text, w):
        lbl = QLabel(text, parent)
        lbl.setGeometry(0, 0, w, self.SECTION_H)
        lbl.setAlignment(Qt.AlignCenter)
        lbl.setFont(QFont("Times New Roman", 14, QFont.Bold))

    def _build_left_info(self, col_w):
        y = self.SECTION_H + 20
        self.photo = QLabel(self.left)
        self.photo.setGeometry(10, y, 90, 100)
        
        self.lbl_name = QLabel(self.left)
        self.lbl_name.setGeometry(118, y + 10, col_w - 136, 60)
        self.lbl_name.setFont(QFont("Times New Roman", 18))
        self.lbl_name.setWordWrap(True)
        
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
        
        full_name = " ".join(filter(None, [
            row.get("last_name"), 
            row.get("first_name"), 
            row.get("middle_name")
        ]))
        if not full_name:
            full_name = "—"
            
        self.lbl_name.setText(full_name)
        
        age_text = "—"
        if row.get('age'):
            age_text = f"{row.get('age', '')} лет"
        self.lbl_age.setText(age_text)
        
        start_time = (row.get('software_start_time') or '').strip()
        if not start_time:
            start_time = "—"
        self.lbl_start.setText(f"Время запуска ПО: <b>{start_time}</b>")
        
        drive = (row.get("drive_duration") or "00:00:00").strip()
        self.lbl_drive.setText(f"Время в дороге: <b>{drive}</b>")
        
        remaining = 9 * 3600 - _parse_hms_to_seconds(drive)
        self.lbl_left.setText(f"Оставшееся время: <b>{_seconds_to_hms(remaining)}</b>")

        id_img = f"ID_{_id_str(self.op_id)}.jpg"
        pm = QPixmap(os.path.join(self.ops_dir, id_img))
        self.photo.setPixmap(
            pm.scaled(90, 100, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        )

    def _update_status(self):
        ok = self.is_verified and self.is_present
        
        self.status_text.setText("Оператор определен" if ok else "Оператор не определен")
        self.status_icon.setPixmap(_make_icon(ok))
        
        banner_bg = '#13FA23' if ok else '#FA1313'
        self.id_banner.setStyleSheet(f"background-color: {banner_bg}; color: black;")
        
        banner_text = f"ID {_id_str(self.op_id)}" if ok else "ID не определен"
        self.id_banner.setText(banner_text)
        
        hint_text = 'Для запуска программы\nнажмите "Далее"' if ok else "Запуск программы\nневозможен"
        self.info_hint.setText(hint_text)
        
        self.btn_next.setEnabled(ok)

    def _start_camera(self):
        self.cap = cv2.VideoCapture(0)
        self.timer.start(30)
        return True

    def _stop_camera(self):
        self.timer.stop()
        self.presence_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

    def _grab_frame(self):
        if not self.cap:
            return
            
        ok, frame = self.cap.read()
        if ok and frame is not None:
            self.last_frame = cv2.flip(frame, 1)
            
            if self.last_face_loc:
                y, right, b, x = self.last_face_loc
                color = (0, 255, 0) if self.last_face_ok else (0, 0, 255)
                cv2.rectangle(self.last_frame, (x, y), (right, b), color, 2)
                
            _draw_to_label_with_dpr(self.last_frame, self.cam_view)

    def _get_reference_encoding_cached(self):
        if self._ref_enc_cache is not None:
            return self._ref_enc_cache
            
        id_img = f"ID_{_id_str(self.op_id)}.jpg"
        ref_path = os.path.join(self.ops_dir, id_img)
        ref_img = _opencv_imread_unicode(ref_path)
        
        if ref_img is not None:
            self._ref_enc_cache, _ = get_cv_face(ref_img)
            
        return self._ref_enc_cache

    def _check_presence(self):
        if self.is_verified and self.last_frame is not None and not self.is_processing:
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
        self.last_face_loc = loc
        self.last_face_ok = live_face_gray is not None

        if loc is None or not cv_compare_faces(ref_face_gray, live_face_gray):
            self.is_verified = False
            _draw_to_label_with_dpr(self.last_frame, self.cam_view)
            QApplication.processEvents()
            
            msg = "Пройти идентификацию заново?"
            res = QMessageBox.question(self, "Идентификация", msg, QMessageBox.Yes | QMessageBox.No)
            
            if res == QMessageBox.Yes:
                QTimer.singleShot(700, self._try_verify)
            return

        self.is_verified = True
        self.is_present = True
        self.presence_timer.start()
        
        frame_draw = self.last_frame.copy()
        y, right, b, x = loc
        cv2.rectangle(frame_draw, (x, y), (right, b), (0, 255, 0), 2)
        _draw_to_label_with_dpr(frame_draw, self.cam_view)
        QApplication.processEvents()
        
        self._update_status()

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
            
        if self.auth_screen:
            self.auth_screen.show()
            
        super().closeEvent(event)