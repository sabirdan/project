import os
from datetime import datetime
import cv2
from PyQt5.QtCore import Qt, QTimer, QThread, QObject, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QWidget, QLabel, QPushButton, QFrame, QMessageBox, 
    QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QApplication
)

from instruction_form import InstructionForm
from utils import (
    make_icon, parse_hms_to_seconds, seconds_to_hms, 
    id_str, draw_to_label_with_dpr, get_cv_face, 
    cv_compare_faces, _opencv_imread_unicode,
    BaseWindow, create_label, COLOR_BG, COLOR_GREEN, 
    COLORbtn_BG, COLOR_DISABLED, getbtn_style
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

class InfoForm(BaseWindow):
    sig_process = pyqtSignal(object, object)

    def __init__(self, start_screen, auth_screen, operator_row: dict, csv_file: str, ops_dir: str):
        super().__init__(1000, 484, "Информация оператора")
        
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
        self.worker.finished.connect(self.on_verification_result)
        self.face_thread.start()

        self.is_processing = False
        self.last_face_loc = None
        self.last_face_ok = False
        self.cap = None
        self.last_frame = None

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.grab_frame)
        
        self.presence_timer = QTimer(self)
        self.presence_timer.timeout.connect(self.check_presence)
        self.presence_timer.setInterval(1000)
        
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self.update_clock)
        self.clock_timer.start(1000)

        self.is_verified = False
        self.is_present = False
        self._ref_enc_cache = None

        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.build_ui(content_layout)
        self.reset_state()
        self.update_status()

        if self.start_camera():
            QTimer.singleShot(1200, self.try_verify)

    def update_clock(self):
        now_str = datetime.now().strftime('%d.%m.%Y / %H:%M:%S')
        self.lbl_dt.setText(f"Дата/время: <b>{now_str}</b>")

    def set_operator_row(self, operator_row: dict):
        self.operator_row = operator_row
        
        id_raw = str(operator_row.get("id", "0")).strip()
        if not id_raw:
            id_raw = "0"
        self.op_id = int(id_raw)
        
        self._ref_enc_cache = None
        self.reset_state()
        self.refresh_left_info()
        self.update_status()
        self.stop_camera()
        
        if self.start_camera():
            QTimer.singleShot(1200, self.try_verify)

    def reset_state(self):
        self.is_verified = False
        self.is_present = False
        self.is_processing = False
        
        if hasattr(self, 'presence_timer'):
            self.presence_timer.stop()

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
        lbl_reg = create_label("Информация оператора", 14, bold=True, align=Qt.AlignCenter)
        lh_layout.addWidget(lbl_reg)

        mh_layout = QHBoxLayout(mid_header)
        self.btn_identify_dummy = QPushButton("Идентификация")
        self.btn_identify_dummy.setFixedSize(200, 35)
        self.btn_identify_dummy.setStyleSheet(getbtn_style())
        mh_layout.addWidget(self.btn_identify_dummy, alignment=Qt.AlignCenter)

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

        self.build_left_info()

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
        self.btn_next = QPushButton("Далее")
        self.btn_next.setFixedSize(100, 34)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet(
            getbtn_style() + 
            f" QPushButton:disabled {{ background-color: {COLOR_DISABLED}; color: gray; }}"
        )
        self.btn_next.clicked.connect(self.finish)
        btn_next_layout.addWidget(self.btn_next)
        right_layout.addLayout(btn_next_layout)

    def build_left_info(self):
        left_layout = QVBoxLayout(self.left)
        left_layout.setContentsMargins(15, 10, 15, 20)
        left_layout.setSpacing(10)

        profile_layout = QHBoxLayout()
        self.photo = QLabel()
        self.photo.setFixedSize(90, 100)
        self.photo.setStyleSheet("background-color: white;")
        profile_layout.addWidget(self.photo)
        
        name_age_layout = QVBoxLayout()
        self.lbl_name = create_label("", 18)
        self.lbl_name.setWordWrap(True)
        name_age_layout.addWidget(self.lbl_name)
        
        self.lbl_age = create_label("", 18)
        name_age_layout.addWidget(self.lbl_age)
        
        profile_layout.addLayout(name_age_layout)
        profile_layout.addStretch()
        left_layout.addLayout(profile_layout)
        
        left_layout.addSpacing(15)

        self.lbl_dt = create_label("", 14)
        left_layout.addWidget(self.lbl_dt)
        
        self.lbl_start = create_label("", 14)
        left_layout.addWidget(self.lbl_start)
        
        self.lbl_drive = create_label("", 14)
        left_layout.addWidget(self.lbl_drive)
        
        self.lbl_left = create_label("", 14)
        left_layout.addWidget(self.lbl_left)

        left_layout.addStretch()
        self.refresh_left_info()

    def refresh_left_info(self):
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
        self.lbl_drive.setText(f"Время в дороге: <span style='padding-left: 10px;'><b>{drive}</b></span>")
        
        remaining = 9 * 3600 - parse_hms_to_seconds(drive)
        self.lbl_left.setText(f"Оставшееся время: <span style='padding-left: 10px;'><b>{seconds_to_hms(remaining)}</b></span>")

        id_img = f"ID_{id_str(self.op_id)}.jpg"
        img_path = os.path.join(self.ops_dir, id_img)
        if os.path.exists(img_path):
            pm = QPixmap(img_path)
            self.photo.setPixmap(
                pm.scaled(90, 100, Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
            )

    def update_status(self):
        ok = self.is_verified and self.is_present
        
        self.status_text.setText("Оператор определен" if ok else "Оператор не определен")
        
        pixmap = make_icon(ok)
        if pixmap:
            self.status_icon.setPixmap(pixmap)
        
        banner_bg = COLOR_GREEN if ok else "red"
        self.id_banner.setStyleSheet(f"background-color: {banner_bg}; color: {COLORbtn_BG};")
        
        banner_text = f"ID {id_str(self.op_id)}" if ok else "ID не определен"
        self.id_banner.setText(banner_text)
        
        hint_text = 'Для запуска программы\nнажмите "Далее"' if ok else "Запуск программы\nневозможен"
        self.info_hint.setText(hint_text)
        
        self.btn_next.setEnabled(ok)

    def start_camera(self):
        self.cap = cv2.VideoCapture(0)
        self.timer.start(30)
        return True

    def stop_camera(self):
        self.timer.stop()
        self.presence_timer.stop()
        if self.cap:
            self.cap.release()
            self.cap = None

    def grab_frame(self):
        if not self.cap:
            return
            
        ok, frame = self.cap.read()
        if ok and frame is not None:
            self.last_frame = cv2.flip(frame, 1)
            
            if self.last_face_loc:
                y, right, b, x = self.last_face_loc
                color = (0, 255, 0) if self.last_face_ok else (0, 0, 255)
                cv2.rectangle(self.last_frame, (x, y), (right, b), color, 2)
                
            draw_to_label_with_dpr(self.last_frame, self.cam_view)

    def get_reference_encoding_cached(self):
        if self._ref_enc_cache is not None:
            return self._ref_enc_cache
            
        id_img = f"ID_{id_str(self.op_id)}.jpg"
        ref_path = os.path.join(self.ops_dir, id_img)
        ref_img = _opencv_imread_unicode(ref_path)
        
        if ref_img is not None:
            self._ref_enc_cache, _ = get_cv_face(ref_img)
            
        return self._ref_enc_cache

    def check_presence(self):
        if self.is_verified and self.last_frame is not None and not self.is_processing:
            ref_enc = self.get_reference_encoding_cached()
            if ref_enc is not None:
                self.is_processing = True
                self.sig_process.emit(self.last_frame.copy(), ref_enc)

    def on_verification_result(self, is_same_person, loc):
        self.is_processing = False
        self.is_present = is_same_person
        self.last_face_loc = loc
        self.last_face_ok = is_same_person
        self.update_status()

    def try_verify(self):
        if self.last_frame is None:
            QTimer.singleShot(500, self.try_verify)
            return

        ref_face_gray = self.get_reference_encoding_cached()
        if ref_face_gray is None:
            QMessageBox.critical(self, "Ошибка", "Эталонное лицо не найдено в файле.")
            return

        live_face_gray, loc = get_cv_face(self.last_frame)
        self.last_face_loc = loc
        self.last_face_ok = live_face_gray is not None

        if loc is None or not cv_compare_faces(ref_face_gray, live_face_gray):
            self.is_verified = False
            draw_to_label_with_dpr(self.last_frame, self.cam_view)
            QApplication.processEvents()
            
            msg = "Пройти идентификацию заново?"
            res = QMessageBox.question(self, "Идентификация", msg, QMessageBox.Yes | QMessageBox.No)
            
            if res == QMessageBox.Yes:
                QTimer.singleShot(700, self.try_verify)
            return

        self.is_verified = True
        self.is_present = True
        self.presence_timer.start()
        
        frame_draw = self.last_frame.copy()
        y, right, b, x = loc
        cv2.rectangle(frame_draw, (x, y), (right, b), (0, 255, 0), 2)
        draw_to_label_with_dpr(frame_draw, self.cam_view)
        QApplication.processEvents()
        
        self.update_status()

    def finish(self):
        self.stop_camera()
        
        if self.face_thread.isRunning():
            self.face_thread.quit()
            self.face_thread.wait()
            
        self.instr_form = InstructionForm(self.operator_row)
        self.instr_form.show()
        self.hide()

    def close_event(self, event):
        self.stop_camera()
        
        if self.face_thread.isRunning():
            self.face_thread.quit()
            self.face_thread.wait()
            
        if self.auth_screen:
            self.auth_screen.show()
            
        super().close_event(event)