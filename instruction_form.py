from utils import *

class InstructionForm(BaseWindow):
    signal_next = pyqtSignal(dict)

    def __init__(self, operator_data=None): 
        super().__init__(1000, 490, "Инструкция")
        self.operator_data = operator_data if operator_data is not None else {}
        
        self.build_ui()

    def build_ui(self):
        main_layout = QVBoxLayout(self.content_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        header_container = QWidget()
        header_container.setFixedHeight(120)
        header_container.setStyleSheet("background-color: white;")
        header_grid = QGridLayout(header_container)
        header_grid.setContentsMargins(0, 0, 0, 0)
        header_grid.setColumnStretch(0, 2)
        header_grid.setColumnStretch(1, 3)
        header_grid.setColumnStretch(2, 2)
        
        self.menu_frame = QFrame()
        self.menu_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        header_grid.addWidget(self.menu_frame, 0, 0)
        
        self.logo_frame = QFrame()
        self.logo_frame.setStyleSheet(f"background-color: {COLOR_GREEN};")
        header_grid.addWidget(self.logo_frame, 0, 1)
        
        self.id_frame = QFrame()
        self.id_frame.setStyleSheet(f"background-color: {COLOR_BG};")
        header_grid.addWidget(self.id_frame, 0, 2)
        
        main_layout.addWidget(header_container)

        menu_layout = QVBoxLayout(self.menu_frame)
        label_menu = create_label("Меню управления", 18, align=Qt.AlignCenter)
        menu_layout.addWidget(label_menu)
        
        buttons_layout = QHBoxLayout()
        button_style = "color: white; border-radius: 18px; font: bold 14px 'Times New Roman';"
        
        button_instruction = QPushButton("Инструкция")
        button_instruction.setFixedHeight(36)
        button_instruction.setStyleSheet(f"background-color: {COLOR_GREEN}; {button_style}")
        buttons_layout.addWidget(button_instruction)
        
        button_analysis = QPushButton("Анализ")
        button_analysis.setFixedHeight(36)
        button_analysis.setStyleSheet(f"background-color: purple; {button_style}")
        buttons_layout.addWidget(button_analysis)
        
        button_control = QPushButton("Управление")
        button_control.setFixedHeight(36)
        button_control.setStyleSheet(f"background-color: purple; {button_style}")
        buttons_layout.addWidget(button_control)
        
        menu_layout.addLayout(buttons_layout)

        logo_layout = QVBoxLayout(self.logo_frame)
        label_logo_title = create_label("НейроБодр", 24, "white", Qt.AlignCenter)
        logo_layout.addWidget(label_logo_title)
        
        separator_line = QFrame()
        separator_line.setFixedHeight(2)
        separator_line.setStyleSheet("background-color: white; margin-left: 40px; margin-right: 40px;")
        logo_layout.addWidget(separator_line)
        
        label_logo_subtitle = create_label("Программа для мониторинга\nсостояния водителей", color="white", align=Qt.AlignCenter)
        logo_layout.addWidget(label_logo_subtitle)

        id_layout = QVBoxLayout(self.id_frame)
        id_layout.setContentsMargins(0, 0, 0, 0)
        
        label_id_title = create_label("Идентификация", align=Qt.AlignCenter)
        label_id_title.setFixedHeight(48)
        label_id_title.setStyleSheet("border-bottom: 4px solid white;")
        id_layout.addWidget(label_id_title)
        
        data_layout = QHBoxLayout()
        data_layout.setContentsMargins(10, 10, 10, 10)
        
        label_operator_defined = create_label("Оператор\nопределен:")
        data_layout.addWidget(label_operator_defined)
        
        first_name = self.operator_data.get("first_name", "")
        last_name = self.operator_data.get("last_name", "")
        label_operator_name = create_label(f"{last_name} {first_name}", 16)
        data_layout.addWidget(label_operator_name)
        id_layout.addLayout(data_layout)

        body_container = QWidget()
        body_container.setStyleSheet("background-color: white;")
        body_layout = QHBoxLayout(body_container)
        body_layout.setContentsMargins(0, 4, 0, 0)
        main_layout.addWidget(body_container, stretch=1)

        self.left_column = QFrame()
        self.left_column.setStyleSheet(f"background-color: {COLOR_BG};")
        body_layout.addWidget(self.left_column, 2)
        
        left_column_layout = QVBoxLayout(self.left_column)
        left_column_layout.setContentsMargins(0, 0, 0, 0)
        
        label_instruction_title = create_label("Инструкция", align=Qt.AlignCenter)
        label_instruction_title.setFixedHeight(44)
        label_instruction_title.setStyleSheet("border-bottom: 4px solid white;")
        left_column_layout.addWidget(label_instruction_title)
        
        inner_left_layout = QVBoxLayout()
        
        instruction_items = [
            ("Зеленый индикатор на видео означает, хорошее состояние оператора.\nОператор бодрствует. ЧСС в пределах нормы. 'Норма'", "circle", "turquoise"),
            ("Желтый индикатор на видео означает 'Внимание' состояние\nоператора выходит за пределы нормы: Падение ЧСС ниже на 20%\nот нормы или повышение на 20%, но ниже критического порога.\nВеки закрыты дольше 4 секунд (микросон). Наклон вперед/вбок\n(эффект 'кивающей головы')", "triangle", "gold"),
            ("Красный индикатор на видео означает, 'Критическое' состояние:\nЧСС ниже на 30% от нормы или больше критического порога.\nНаклон головы вперед/вбок (дольше 7 секунд) веки закрыты", "square", "red")
        ]
        
        for text, shape, color in instruction_items:
            row_layout = QHBoxLayout()
            shape_widget = ShapeWidget(shape, color)
            row_layout.addWidget(shape_widget, alignment=Qt.AlignTop)
            
            label_text = create_label(text)
            row_layout.addWidget(label_text, stretch=1)
            
            inner_left_layout.addLayout(row_layout)
            
        left_column_layout.addLayout(inner_left_layout)

        self.right_column = QFrame()
        self.right_column.setStyleSheet(f"background-color: {COLOR_BG};")
        body_layout.addWidget(self.right_column, 1)
        
        right_column_layout = QVBoxLayout(self.right_column)
        right_column_layout.setContentsMargins(0, 0, 0, 0)
        
        label_right_title = create_label("Вид подключения", align=Qt.AlignCenter)
        label_right_title.setFixedHeight(44)
        label_right_title.setStyleSheet("border-bottom: 4px solid white;")
        right_column_layout.addWidget(label_right_title)

        inner_right_layout = QVBoxLayout()
        inner_right_layout.setContentsMargins(10, 10, 10, 10)
        
        images_layout = QHBoxLayout()
        
        image_names = ["hand1.png", "hand2.png"]
        for name in image_names:
            image_box = QLabel()
            image_box.setStyleSheet("background-color: white;")
            image_box.setAlignment(Qt.AlignCenter)
            pixmap = QPixmap(f"assets/{name}").scaled(100, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            image_box.setPixmap(pixmap)
            images_layout.addWidget(image_box)
            
        inner_right_layout.addLayout(images_layout)
        
        label_connection_hint = create_label("Наклеить электроды как показано\nна рисунке и подключить контакты")
        inner_right_layout.addWidget(label_connection_hint)
        
        self.button_next = create_button("Далее", 110, 36, self.go_next)
        inner_right_layout.addWidget(self.button_next, alignment=Qt.AlignRight)
        right_column_layout.addLayout(inner_right_layout)

    def go_next(self):
        self.signal_next.emit(self.operator_data)
        self.hide()