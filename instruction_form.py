from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QWidget, QPushButton, QFrame, QVBoxLayout, QHBoxLayout, QSpacerItem, QSizePolicy, QLabel
)

from utils import (
    BaseWindow, ShapeWidget, create_label,
    COLOR_BG, COLOR_GREEN, get_btn_style
)

class InstructionForm(BaseWindow):
    def __init__(self, operator_row: dict = None):
        super().__init__(1000, 484, "Инструкция и подключение")
        
        self.operator_row = operator_row or {}
        self.analysis_form = None
        self.control_form = None

        content_layout = QVBoxLayout(self.content_container)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self._build_ui(content_layout)

    def _build_ui(self, parent_layout):
        header_container = QWidget()
        header_container.setFixedHeight(120)
        header_container.setStyleSheet("background-color: white;")
        
        header_layout = QHBoxLayout(header_container)
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)

        menu_frame = QFrame()
        menu_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        logo_frame = QFrame()
        logo_frame.setStyleSheet(f"background-color: {COLOR_GREEN};")
        id_frame = QFrame()
        id_frame.setStyleSheet(f"background-color: {COLOR_BG};")

        header_layout.addWidget(menu_frame, stretch=1)
        header_layout.addWidget(logo_frame, stretch=1)
        header_layout.addWidget(id_frame, stretch=1)

        menu_vbox = QVBoxLayout(menu_frame)
        menu_vbox.setContentsMargins(10, 15, 10, 15)
        
        lbl_menu = create_label("Меню управления", 18, align=Qt.AlignCenter)
        menu_vbox.addWidget(lbl_menu)
        menu_vbox.addStretch()
        
        btn_hbox = QHBoxLayout()
        b_style = "color: white; border-radius: 18px; font-family: 'Times New Roman'; font-size: 14px; font-weight: bold;"
        
        self.btn_instr = QPushButton("Инструкция")
        self.btn_instr.setFixedHeight(36)
        self.btn_instr.setStyleSheet(f"QPushButton {{ background-color: {COLOR_GREEN}; {b_style} }}")
        
        self.btn_analysis = QPushButton("Анализ")
        self.btn_analysis.setFixedHeight(36)
        self.btn_analysis.setStyleSheet(f"QPushButton {{ background-color: purple; {b_style} }}")
        self.btn_analysis.clicked.connect(self._open_analysis)
        
        self.btn_control = QPushButton("Управление")
        self.btn_control.setFixedHeight(36)
        self.btn_control.setStyleSheet(f"QPushButton {{ background-color: purple; {b_style} }}")
        self.btn_control.clicked.connect(self._open_control)
        
        btn_hbox.addWidget(self.btn_instr)
        btn_hbox.addWidget(self.btn_analysis)
        btn_hbox.addWidget(self.btn_control)
        menu_vbox.addLayout(btn_hbox)

        logo_vbox = QVBoxLayout(logo_frame)
        logo_vbox.setContentsMargins(0, 10, 0, 10)
        logo_vbox.setSpacing(5)
        
        lbl_logo = create_label("НейроБодр", 24, bold=True, color="white", align=Qt.AlignCenter)
        logo_vbox.addWidget(lbl_logo)
        
        line_layout = QHBoxLayout()
        line_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        line = QFrame()
        line.setFixedHeight(2)
        line.setStyleSheet("background-color: white;")
        line.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        line_layout.addWidget(line, stretch=3) 
        line_layout.addSpacerItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        logo_vbox.addLayout(line_layout)
        
        lbl_desc = create_label("Программа для мониторинга\nсостояния водителей", 14, color="white", align=Qt.AlignCenter)
        logo_vbox.addWidget(lbl_desc)

        id_vbox = QVBoxLayout(id_frame)
        id_vbox.setContentsMargins(0, 0, 0, 0)
        id_vbox.setSpacing(0)
        
        lbl_id_title = create_label("Идентификация", 14, align=Qt.AlignCenter)
        lbl_id_title.setFixedHeight(44)
        id_vbox.addWidget(lbl_id_title)
        
        id_sep = QFrame()
        id_sep.setFixedHeight(4)
        id_sep.setStyleSheet("background-color: white;")
        id_vbox.addWidget(id_sep)
        
        id_data_hbox = QHBoxLayout()
        id_data_hbox.setContentsMargins(20, 10, 20, 10)
        
        lbl_op_status = create_label("Оператор\nопределен:", 14)
        
        f_name = self.operator_row.get('first_name', '')
        l_name = self.operator_row.get('last_name', '')
        self.lbl_op_name = create_label(f"{l_name} {f_name}", 16)
        
        id_data_hbox.addWidget(lbl_op_status)
        id_data_hbox.addStretch()
        id_data_hbox.addWidget(self.lbl_op_name)
        
        id_vbox.addLayout(id_data_hbox)

        parent_layout.addWidget(header_container)

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
        right_header = QFrame()
        right_header.setStyleSheet(f"background-color: {COLOR_BG};")

        top_layout.addWidget(left_header, stretch=2)
        top_layout.addWidget(right_header, stretch=1)

        lh_layout = QVBoxLayout(left_header)
        lbl_instruction = create_label("Инструкция", 14, align=Qt.AlignCenter)
        lh_layout.addWidget(lbl_instruction)

        rh_layout = QVBoxLayout(right_header)
        lbl_conn = create_label("Вид подключения", 14, align=Qt.AlignCenter)
        rh_layout.addWidget(lbl_conn)

        body_main_layout.addWidget(top_row)

        bottom_row = QWidget()
        bottom_layout = QHBoxLayout(bottom_row)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        bottom_layout.setSpacing(4)

        self.left_col = QFrame()
        self.left_col.setStyleSheet(f"background-color: {COLOR_BG};")
        self.right_col = QFrame()
        self.right_col.setStyleSheet(f"background-color: {COLOR_BG};")

        bottom_layout.addWidget(self.left_col, stretch=2)
        bottom_layout.addWidget(self.right_col, stretch=1)

        body_main_layout.addWidget(bottom_row, stretch=1)
        parent_layout.addWidget(body_container, stretch=1)

        self._build_instruction_content()
        self._build_connection_content()

    def _build_instruction_content(self):
        left_layout = QVBoxLayout(self.left_col)
        left_layout.setContentsMargins(15, 10, 15, 10)
        left_layout.setSpacing(15)
        
        data = [
            (
                "Зеленый индикатор на видео означает, хорошее состояние оператора.\n"
                "Оператор бодрствует. ЧСС в пределах нормы. 'Норма'", 
                "circle", "turquoise"
            ),
            (
                "Желтый индикатор на видео означает 'Внимание' состояние\n"
                "оператора выходит за пределы нормы: Падение ЧСС ниже на 20%\n"
                "от нормы или повышение на 20%, но ниже критического порога.\n"
                "Веки закрыты дольше 4 секунд (микросон). Наклон вперед/вбок\n"
                "(эффект 'кивающей головы')", 
                "triangle", "gold"
            ),
            (
                "Красный индикатор на видео означает, 'Критическое' состояние:\n"
                "ЧСС ниже на 30% от нормы или больше критического порога.\n"
                "Наклон головы вперед/вбок (дольше 7 секунд) веки закрыты", 
                "square", "red"
            )
        ]

        for text, shape, color in data:
            row_layout = QHBoxLayout()
            row_layout.setContentsMargins(0, 0, 0, 0)
            row_layout.setSpacing(15)
            
            icon = ShapeWidget(shape, color)
            row_layout.addWidget(icon, alignment=Qt.AlignTop)
            
            lbl = create_label(text, 11)
            lbl.setWordWrap(True)
            row_layout.addWidget(lbl, stretch=1)
            
            left_layout.addLayout(row_layout)
            
        left_layout.addStretch()

    def _build_connection_content(self):
        right_layout = QVBoxLayout(self.right_col)
        right_layout.setContentsMargins(20, 20, 20, 20)
        
        images_hbox = QHBoxLayout()
        images_hbox.setSpacing(20)
        
        for img_name in ["hand1.png", "hand2.png"]:
            box = QLabel()
            box.setStyleSheet("background-color: white;")
            try:
                pix = QPixmap(f"assets/{img_name}")
                box.setPixmap(pix.scaled(100, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            except:
                pass
            box.setAlignment(Qt.AlignCenter)
            images_hbox.addWidget(box)
            
        right_layout.addLayout(images_hbox)
        right_layout.addSpacing(15)
        
        lbl_hint = create_label("Наклеить электроды как показано\nна рисунке и подключить контакты", 11)
        lbl_hint.setWordWrap(True)
        right_layout.addWidget(lbl_hint)
        right_layout.addStretch()
        
        btn_next_layout = QHBoxLayout()
        btn_next_layout.addStretch()
        self.btn_next = QPushButton("Далее")
        self.btn_next.setFixedSize(110, 36)
        self.btn_next.setCursor(Qt.PointingHandCursor)
        self.btn_next.setStyleSheet(get_btn_style())
        self.btn_next.clicked.connect(self._open_analysis)
        btn_next_layout.addWidget(self.btn_next)
        
        right_layout.addLayout(btn_next_layout)

    def _open_control(self):
        from control_form import ControlForm 
        if self.control_form is None:
            self.control_form = ControlForm(self.operator_row)
        self.control_form.show()
        self.hide()

    def _open_analysis(self):
        from analysis_form import AnalysisForm 
        if self.analysis_form is None:
            self.analysis_form = AnalysisForm(self.operator_row)
        self.analysis_form.show()
        self.hide()