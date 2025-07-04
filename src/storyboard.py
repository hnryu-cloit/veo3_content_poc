import json
import os
from datetime import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTextEdit,
                             QPushButton, QLabel, QScrollArea, QFrame,
                             QWidget, QLineEdit, QSpinBox, QComboBox,
                             QMessageBox, QStackedWidget, QStyledItemDelegate,
                             QGroupBox, QInputDialog, QTableWidget,
                             QTableWidgetItem, QHeaderView)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap, QTextDocument
from PIL import Image

from common.gemini import Gemini

class ImageGenerationThread(QThread):
    scene_completed = pyqtSignal(int, object, str)
    generation_completed = pyqtSignal()

    def __init__(self, scenes, api_key=None):
        super().__init__()
        self.scenes = scenes
        self.temp_folder = './temp'

        os.makedirs(self.temp_folder, exist_ok=True)

    def run(self):
        """각 씬에 대해 이미지 생성"""
        for i, scene in enumerate(self.scenes):
            try:
                image_obj = self.generate_scene_image(scene, i + 1)
                self.scene_completed.emit(i + 1, image_obj, "")
            except Exception as e:
                self.scene_completed.emit(i + 1, None, str(e))
            finally:
                import gc
                gc.collect()  # 각 씬 처리 후 메모리 정리
        self.generation_completed.emit()

    def generate_scene_image(self, scene, scene_number):
        """실제 이미지 생성 함수 (Imagen4 API 사용)"""
        prompt = self.create_scene_image_prompt(scene)
        try:
            # 임시로 더미 이미지 생성 (실제로는 Imagen4 API 호출)
            # dummy_image = Image.new('RGB', (512, 512), color='lightgray')
            dummy_image = self.gemini._call_imagen_text(prompt)
            temp_path = os.path.join(self.temp_folder, f"scene_{scene_number}.png")
            dummy_image.save(temp_path, 'PNG')
            return temp_path
        finally:
            import gc
            gc.collect()

    def create_scene_image_prompt(self, scene):
        prompt_parts = []

        if 'visual' in scene:
            prompt_parts.append(f"Visual: {scene['visual']}")
        if 'description' in scene:
            prompt_parts.append(f"Description: {scene['description']}")
        if 'mood' in scene:
            prompt_parts.append(f"Mood: {scene['mood']}")

        return " | ".join(prompt_parts)


class SceneEditWidget(QWidget):
    """개별 씬(장면) 편집을 위한 위젯"""

    def __init__(self, scene_data, scene_number):
        super().__init__()
        self.scene_data = scene_data
        self.scene_number = scene_number
        self.init_ui()

    def init_ui(self):
        # 메인 그룹박스
        main_group = QGroupBox(f'#{self.scene_number}')
        main_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 13px;
                margin-top: 5px;
                padding-top: 5px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #000000;
            }
        """)

        layout = QVBoxLayout(main_group)

        # 씬 길이 편집
        duration_group = QGroupBox('씬 길이')
        duration_layout = QHBoxLayout()
        self.duration_edit = QLineEdit(str(self.scene_data.get('duration', '5초')))
        self.duration_edit.setPlaceholderText('예: 5초')
        duration_layout.addWidget(self.duration_edit)
        duration_group.setLayout(duration_layout)
        layout.addWidget(duration_group)

        # 화면 내용 편집
        visual_group = QGroupBox('화면 내용')
        visual_layout = QVBoxLayout()
        self.visual_edit = QTextEdit()
        self.visual_edit.setPlainText(self.scene_data.get('visual', ''))
        self.visual_edit.setPlaceholderText('인물 배치, 카메라 앵글, 배경 설정 등을 입력하세요')
        self.visual_edit.setMaximumHeight(50)
        visual_layout.addWidget(self.visual_edit)
        visual_group.setLayout(visual_layout)
        layout.addWidget(visual_group)

        # 음성/음향 편집
        audio_group = QGroupBox('음성/음향')
        audio_layout = QVBoxLayout()
        self.audio_edit = QTextEdit()
        self.audio_edit.setPlainText(self.scene_data.get('audio', ''))
        self.audio_edit.setPlaceholderText('나레이션, 배경 음악, 효과음 등을 입력하세요')
        self.audio_edit.setMaximumHeight(50)
        audio_layout.addWidget(self.audio_edit)
        audio_group.setLayout(audio_layout)
        layout.addWidget(audio_group)

        # 자막/텍스트 편집
        text_group = QGroupBox('자막/텍스트')
        text_layout = QVBoxLayout()
        self.text_edit = QTextEdit()
        self.text_edit.setPlainText(self.scene_data.get('text', ''))
        self.text_edit.setPlaceholderText('화면에 표시될 자막이나 텍스트를 입력하세요')
        self.text_edit.setMaximumHeight(30)
        text_layout.addWidget(self.text_edit)
        text_group.setLayout(text_layout)
        layout.addWidget(text_group)

        # 씬 설명 편집
        description_group = QGroupBox('씬 설명')
        description_layout = QVBoxLayout()
        self.description_edit = QTextEdit()
        self.description_edit.setPlainText(self.scene_data.get('description', ''))
        self.description_edit.setPlaceholderText('씬에 대한 전체적인 설명을 입력하세요')
        self.description_edit.setMaximumHeight(50)
        description_layout.addWidget(self.description_edit)
        description_group.setLayout(description_layout)
        layout.addWidget(description_group)

        # 분위기/무드 선택
        mood_group = QGroupBox('분위기/무드')
        mood_layout = QHBoxLayout()
        self.mood_combo = QComboBox()
        self.mood_combo.addItems(['밝은', '어두운', '신비로운', '활기찬', '차분한', '극적인', '로맨틱한'])
        self.mood_combo.setEditable(True)
        current_mood = self.scene_data.get('mood', '밝은')
        if current_mood in ['밝은', '어두운', '신비로운', '활기찬', '차분한', '극적인', '로맨틱한']:
            self.mood_combo.setCurrentText(current_mood)
        mood_layout.addWidget(self.mood_combo)
        mood_group.setLayout(mood_layout)
        layout.addWidget(mood_group)

        # 전체 레이아웃
        widget_layout = QVBoxLayout()
        widget_layout.addWidget(main_group)
        self.setLayout(widget_layout)

        # 공통 스타일 적용
        self.apply_common_styles()

    def apply_common_styles(self):
        """공통 스타일 적용"""
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 0.5px solid #ccc;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTextEdit, QLineEdit {
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QTextEdit:focus, QLineEdit:focus {
                border: 1px solid #2196F3;
            }
            QComboBox {
                border: 0.5px solid #ccc;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
                min-width: 100px;
            }
            QComboBox:focus {
                border: 2px solid #2196F3;
            }
        """)

    def get_scene_data(self):
        """편집된 씬 데이터 반환"""
        return {
            'scene_number': self.scene_number,
            'duration': self.duration_edit.text(),
            'visual': self.visual_edit.toPlainText(),
            'audio': self.audio_edit.toPlainText(),
            'text': self.text_edit.toPlainText(),
            'description': self.description_edit.toPlainText(),
            'mood': self.mood_combo.currentText()
        }


class WordWrapDelegate(QStyledItemDelegate):
    """텍스트 줄바꿈을 지원하는 커스텀 델리게이트"""

    def paint(self, painter, option, index):
        # 텍스트 가져오기
        text = index.data(Qt.DisplayRole)
        if not text:
            return super().paint(painter, option, index)

        # 텍스트 문서 생성
        doc = QTextDocument()
        doc.setPlainText(str(text))
        doc.setTextWidth(option.rect.width() - 10)  # 패딩 고려

        # 배경 그리기
        painter.save()
        painter.fillRect(option.rect, option.palette.base())

        # 텍스트 그리기
        painter.translate(option.rect.x() + 5, option.rect.y() + 5)  # 패딩
        doc.drawContents(painter)
        painter.restore()

    def sizeHint(self, option, index):
        # 텍스트 가져오기
        text = index.data(Qt.DisplayRole)
        if not text:
            return super().sizeHint(option, index)

        # 텍스트 문서 생성하여 필요한 높이 계산
        doc = QTextDocument()
        doc.setPlainText(str(text))
        doc.setTextWidth(option.rect.width() - 10)  # 패딩 고려

        # 높이 계산 (최소 30, 최대 150)
        height = max(30, min(150, int(doc.size().height()) + 10))
        return option.rect.adjusted(0, 0, 0, height - option.rect.height()).size()


class StoryboardDialog(QDialog):
    """스토리보드 결과를 표시하는 다이얼로그"""

    def __init__(self, storyboard_data, parent=None):
        super().__init__(parent)
        self.storyboard_data = storyboard_data
        self.selected_storyboard = None
        self.edited_scenes = []
        self.generated_images = {}

        # 기본 output 폴더 설정
        self.output_folder = './output'
        self.current_project_folder = None

        # output 폴더가 없으면 생성
        if not os.path.exists(self.output_folder):
            os.makedirs(self.output_folder)

        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('스토리보드 생성 및 편집')
        self.setGeometry(100, 100, 500, 900)

        # 메인 레이아웃
        main_layout = QVBoxLayout()

        # 제목
        title_label = QLabel('스토리보드 생성 및 편집')
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                color: #000000;
                padding: 20px;
                border-radius: 8px;
                margin-bottom: 8px;
            }
        """)
        main_layout.addWidget(title_label)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # 단계별 화면 전환
        self.stacked_widget = QStackedWidget()

        # 1단계: 스토리보드 선택
        self.create_selection_page()

        # 2단계: 씬(장면) 편집
        self.create_edit_page()

        # 3단계: 이미지 생성 및 최종 결과
        self.create_generation_page()

        main_layout.addWidget(self.stacked_widget)

        self.setLayout(main_layout)

        # 전체 다이얼로그 스타일 적용
        self.setStyleSheet("""
            QDialog {
                background-color: #f9f9f9;
            }
        """)

    def create_selection_page(self):
        """스토리보드 선택 페이지 생성"""
        selection_widget = QWidget()
        layout = QVBoxLayout()

        # 안내 문구
        info_label = QLabel('원하시는 스토리보드를 선택해 주세요')
        info_label.setStyleSheet("""
            QLabel {
                font-size: 15px;
                font-weight: bold;
                color: #333;
                border-radius: 8px;
                margin: 8px;
            }
        """)
        layout.addWidget(info_label)

        # 스토리보드 옵션 버튼들
        button_layout = QVBoxLayout()

        for idx, key in enumerate(self.storyboard_data.keys()):
            if key.startswith('storyboard'):
                storyboard = self.storyboard_data[key]
                title = f"#{idx + 1}. {storyboard.get('title', f'스토리보드 {key[-1]}')}"

                # 버튼 컨테이너
                button_container = QFrame()
                button_container.setStyleSheet("""
                    QFrame {
                        background-color: white;
                        border: 2px solid #2196F3;
                        border-radius: 8px;
                        margin: 2px;
                    }
                    QFrame:hover {
                        background-color: #e3f2fd;
                    }
                """)

                container_layout = QVBoxLayout(button_container)

                button = QPushButton(title)
                button.setStyleSheet("""
                    QPushButton {
                        background-color: transparent;
                        border: none;
                        padding: 10px;
                        font-size: 14px;
                        font-weight: bold;
                        color: #1976D2;
                        text-align: left;
                    }
                    QPushButton:hover {
                        color: #0d47a1;
                    }
                """)
                button.clicked.connect(lambda checked, k=key: self.select_storyboard(k))
                container_layout.addWidget(button)

                button_layout.addWidget(button_container)

        layout.addLayout(button_layout)
        layout.addStretch()

        selection_widget.setLayout(layout)
        self.stacked_widget.addWidget(selection_widget)

    def create_edit_page(self):
        edit_widget = QWidget()
        layout = QVBoxLayout()
        self.edit_info_label = QLabel()
        self.edit_info_label.setStyleSheet("""
            QLabel {
                font-size: 14px;
                font-weight: bold;
                color: #000000;
                border-radius: 8px;
            }
        """)
        self.edit_info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.edit_info_label)

        scene_control_group = QGroupBox('씬 설정')
        scene_control_group.setStyleSheet("""
            QGroupBox {
                font-size: 13pt;
                font-weight: bold;
            }
        """)
        scene_control_layout = QHBoxLayout()
        scene_count_label = QLabel('씬 개수:')
        scene_count_label.setStyleSheet("""
            QLabel {
                font-size: 13pt;
                font-weight: bold;
            }
        """)
        scene_control_layout.addWidget(scene_count_label)
        self.scene_count_spin = QSpinBox()
        self.scene_count_spin.setRange(1, 16)  # 최대 16개로 제한
        self.scene_count_spin.setValue(8)
        self.scene_count_spin.valueChanged.connect(self.update_scene_count)
        scene_control_layout.addWidget(self.scene_count_spin)
        scene_control_layout.addStretch()
        scene_control_group.setLayout(scene_control_layout)
        layout.addWidget(scene_control_group)

        # 스크롤 영역
        scroll = QScrollArea()
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        scroll.setWidget(self.scroll_widget)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        layout.addWidget(scroll)

        # 하단 버튼들
        button_layout = QHBoxLayout()

        back_button = QPushButton('이전')
        back_button.clicked.connect(self.go_back_to_selection)
        back_button.setStyleSheet(self.get_button_style('#757575'))
        button_layout.addWidget(back_button)

        button_layout.addStretch()

        generate_button = QPushButton('이미지 생성')
        generate_button.clicked.connect(self.start_image_generation)
        generate_button.setStyleSheet(self.get_button_style('#4CAF50'))
        button_layout.addWidget(generate_button)

        layout.addLayout(button_layout)
        edit_widget.setLayout(layout)
        self.stacked_widget.addWidget(edit_widget)

    def create_generation_page(self):
        """이미지 생성 및 최종 결과 페이지"""
        generation_widget = QWidget()
        layout = QVBoxLayout()

        # 결과 표시 영역
        self.result_scroll = QScrollArea()
        self.result_widget = QWidget()
        self.result_layout = QVBoxLayout(self.result_widget)
        self.result_scroll.setWidget(self.result_widget)
        self.result_scroll.setWidgetResizable(True)
        self.result_scroll.setStyleSheet("""
            QScrollArea {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.result_scroll)

        # 하단 버튼들
        button_layout = QHBoxLayout()

        back_edit_button = QPushButton('이전 화면으로')
        back_edit_button.clicked.connect(self.go_back_to_edit)
        back_edit_button.setStyleSheet(self.get_button_style('#757575'))
        button_layout.addWidget(back_edit_button)

        button_layout.addStretch()

        # 폴더 설정 버튼 추가
        folder_button = QPushButton('저장폴더 설정')
        folder_button.clicked.connect(self.set_output_folder)
        folder_button.setStyleSheet(self.get_button_style('#FF9800'))
        button_layout.addWidget(folder_button)

        save_button = QPushButton('결과 저장')
        save_button.clicked.connect(self.save_final_result)
        save_button.setStyleSheet(self.get_button_style('#2196F3'))
        button_layout.addWidget(save_button)

        close_button = QPushButton('닫기')
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet(self.get_button_style('#757575'))
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)
        generation_widget.setLayout(layout)
        self.stacked_widget.addWidget(generation_widget)

    def select_storyboard(self, storyboard_key):
        """스토리보드 선택 및 편집 페이지로 이동"""
        self.selected_storyboard = self.storyboard_data[storyboard_key]

        # 편집 페이지 정보 업데이트
        title = self.selected_storyboard.get('title')
        self.edit_info_label.setText(f"{title}")

        # 기존 씬 편집 위젯들 제거
        for i in reversed(range(self.scroll_layout.count())):
            self.scroll_layout.itemAt(i).widget().setParent(None)

        # 새 씬 편집 위젯들 생성
        self.create_scene_edit_widgets()

        # 편집 페이지로 이동
        self.stacked_widget.setCurrentIndex(1)

    def create_scene_edit_widgets(self):
        """씬 편집 위젯들 생성"""
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()  # 메모리 해제

        scenes = self.selected_storyboard.get('scenes', [])
        target_scene_count = self.scene_count_spin.value()

        while len(scenes) < target_scene_count:
            scenes.append({
                'scene_number': len(scenes) + 1,
                'duration': '',
                'visual': '',
                'audio': '',
                'text': '',
                'description': '',
                'mood': ''
            })
        scenes = scenes[:target_scene_count]

        self.scene_edit_widgets = []
        for i, scene in enumerate(scenes):
            scene_widget = SceneEditWidget(scene, i + 1)
            self.scene_edit_widgets.append(scene_widget)
            self.scroll_layout.addWidget(scene_widget)

    def update_scene_count(self):
        if hasattr(self, 'scene_edit_widgets'):
            self.create_scene_edit_widgets()

    def go_back_to_selection(self):
        """선택 페이지로 돌아가기"""
        self.stacked_widget.setCurrentIndex(0)

    def go_back_to_edit(self):
        """편집 페이지로 돌아가기"""
        self.stacked_widget.setCurrentIndex(1)

    def start_image_generation(self):
        """이미지 생성 시작"""
        # 편집된 씬 데이터 수집
        self.edited_scenes = []
        for widget in self.scene_edit_widgets:
            self.edited_scenes.append(widget.get_scene_data())

        # 이미지 생성 페이지로 이동
        self.stacked_widget.setCurrentIndex(2)

        # 이미지 생성 스레드 시작
        self.image_thread = ImageGenerationThread(self.edited_scenes)
        self.image_thread.scene_completed.connect(self.on_scene_completed)
        self.image_thread.generation_completed.connect(self.on_generation_completed)
        self.image_thread.start()

    def on_generation_completed(self):
        """모든 이미지 생성 완료"""
        # 결과 표시
        self.display_final_results()

    def display_final_results(self):
        """최종 결과 표시"""
        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        for i, scene in enumerate(self.edited_scenes):
            scene_number = i + 1
            scene_container = QWidget()
            scene_container.setStyleSheet("""
                QWidget {
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 8px;
                    margin: 5px;
                    padding: 5px;
                }
            """)
            scene_layout = QVBoxLayout(scene_container)
            title_label = QLabel(f"#{scene_number}: ({scene.get('duration', '')})")
            title_label.setStyleSheet("""
                QLabel {
                    font-weight: bold;
                    font-size: 14px;
                    color: #333;
                    padding: 5px;
                    background-color: #f0f0f0;
                    border-radius: 1px;
                    margin-bottom: 5px;
                }
            """)
            title_label.setAlignment(Qt.AlignCenter)
            scene_layout.addWidget(title_label)
            image_widget = self.create_image_widget(scene_number)
            scene_layout.addWidget(image_widget)
            info_table = self.create_scene_info_table(scene)
            scene_layout.addWidget(info_table)
            self.result_layout.addWidget(scene_container)

    def create_image_widget(self, scene_number):
        """이미지 위젯 생성"""
        image_container = QWidget()
        image_container.setFixedHeight(350)
        image_layout = QVBoxLayout(image_container)
        image_label = QLabel()
        image_label.setFixedSize(320, 320)
        image_label.setStyleSheet("""
            QLabel {
                border: 2px solid #ccc;
                background-color: #f9f9f9;
                border-radius: 1px;
            }
        """)
        image_label.setAlignment(Qt.AlignCenter)

        if scene_number in self.generated_images:
            image_info = self.generated_images[scene_number]
            if isinstance(image_info, str) and os.path.exists(image_info):
                pixmap = QPixmap(image_info)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(300, 300, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                    image_label.setPixmap(scaled_pixmap)
                else:
                    image_label.setText("이미지 로딩 실패")
            elif isinstance(image_info, dict) and 'error' in image_info:
                image_label.setText(f"오류: {image_info['error']}")
            else:
                image_label.setText("이미지 파일 없음")
        else:
            image_label.setText("이미지 없음")

        image_layout.addWidget(image_label, alignment=Qt.AlignCenter)
        return image_container

    def on_scene_completed(self, scene_number, file_path, error_message):
        if error_message:
            self.generated_images[scene_number] = {'error': error_message}
        else:
            self.generated_images[scene_number] = file_path

    def create_scene_info_table(self, scene):
        """씬 정보 테이블 생성"""
        info_table = QTableWidget(4, 2)

        # 헤더 제거
        info_table.horizontalHeader().setVisible(False)
        info_table.verticalHeader().setVisible(False)

        # 테이블 설정
        info_table.setHorizontalHeaderLabels(['항목', '내용'])
        info_table.horizontalHeader().setStretchLastSection(True)

        # 열 너비 설정
        info_table.setColumnWidth(0, 80)

        # 테이블 스타일
        info_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                gridline-color: #ddd;
                border: 1px solid #ccc;
                border-radius: 4px;
            }
            QTableWidget::item {
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #e3f2fd;
            }
        """)

        # 테이블 데이터 설정
        items = [
            ('장면', scene.get('visual', '')),
            ('음성', scene.get('audio', '')),
            ('자막', scene.get('text', '')),
            ('설명', scene.get('description', ''))
        ]

        for row, (label, content) in enumerate(items):
            # 항목 열
            item_cell = QTableWidgetItem(label)
            item_cell.setFlags(item_cell.flags() & ~Qt.ItemIsEditable)
            item_cell.setTextAlignment(Qt.AlignCenter)
            item_cell.setBackground(Qt.lightGray)
            info_table.setItem(row, 0, item_cell)

            # 내용 열
            content_cell = QTableWidgetItem(content)
            content_cell.setTextAlignment(Qt.AlignLeft | Qt.AlignTop)
            content_cell.setFlags(content_cell.flags() | Qt.ItemIsEditable)
            info_table.setItem(row, 1, content_cell)

            # 행 높이 계산
            text_lines = len(content.split('\n')) if content else 1
            row_height = max(30, min(100, text_lines * 25))
            info_table.setRowHeight(row, row_height)

        # 전체 높이 계산 및 설정
        total_height = sum(info_table.rowHeight(i) for i in range(4))
        info_table.setFixedHeight(total_height + 30)

        return info_table

    def set_output_folder(self):
        """저장 폴더 설정"""
        folder_name, ok = QInputDialog.getText(
            self,
            '저장 폴더 설정',
            '새로운 프로젝트 폴더명을 입력하세요:\n(./output 폴더 내에 생성됩니다)',
            text=f"storyboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        )

        if ok and folder_name.strip():
            # 폴더명 정리
            folder_name = folder_name.strip()
            folder_name = "".join(c for c in folder_name if c.isalnum() or c in (' ', '-', '_')).rstrip()

            if not folder_name:
                QMessageBox.warning(self, '입력 오류', '올바른 폴더명을 입력해주세요.')
                return

            # 전체 경로 생성
            full_path = os.path.join(self.output_folder, folder_name)

            try:
                # 폴더 생성
                if not os.path.exists(full_path):
                    os.makedirs(full_path)
                    self.current_project_folder = full_path
                    QMessageBox.information(self, '폴더 설정 완료', f'저장 폴더가 설정되었습니다:\n{full_path}')
                else:
                    # 이미 존재하는 폴더인 경우 사용자에게 확인
                    reply = QMessageBox.question(
                        self, '폴더 존재',
                        f'폴더가 이미 존재합니다:\n{full_path}\n\n기존 폴더를 사용하시겠습니까?',
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        self.current_project_folder = full_path
                        QMessageBox.information(self, '폴더 설정 완료', f'저장 폴더가 설정되었습니다:\n{full_path}')

            except Exception as e:
                QMessageBox.critical(self, '폴더 생성 오류', f'폴더 생성 중 오류가 발생했습니다:\n{str(e)}')

    def save_final_result(self):
        """최종 결과 저장"""
        self.collect_edited_table_data()

        if not self.current_project_folder:
            reply = QMessageBox.question(
                self, '저장 폴더 미설정',
                '저장 폴더가 설정되지 않았습니다.\n폴더를 먼저 설정하시겠습니까?',
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                self.set_output_folder()
                if not self.current_project_folder:
                    return
            else:
                return

        file_name, ok = QInputDialog.getText(
            self,
            '파일명 입력',
            '저장할 파일명을 입력하세요:',
            text='final_storyboard.json'
        )

        if not ok or not file_name.strip():
            return

        if not file_name.endswith('.json'):
            file_name += '.json'

        file_path = os.path.join(self.current_project_folder, file_name)

        try:
            # 임시 이미지 이동
            images_folder = os.path.join(self.current_project_folder, 'images')
            if not os.path.exists(images_folder):
                os.makedirs(images_folder)

            image_paths = {}
            for scene_number, image_info in self.generated_images.items():
                if isinstance(image_info, str) and os.path.exists(image_info):
                    new_filename = f"scene_{scene_number}.png"
                    new_path = os.path.join(images_folder, new_filename)
                    import shutil
                    shutil.move(image_info, new_path)  # 임시 파일 이동
                    image_paths[scene_number] = new_path

            final_data = {
                'title': self.selected_storyboard.get('title'),
                'scenes': self.edited_scenes,
                'generated_images': image_paths,  # 이동된 이미지 경로 저장
                'creation_date': str(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
                'project_folder': self.current_project_folder
            }

            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, ensure_ascii=False, indent=2)

            QMessageBox.information(self, '저장 완료', f'스토리보드가 저장되었습니다:\n{file_path}')

        except Exception as e:
            QMessageBox.critical(self, '저장 오류', f'파일 저장 중 오류가 발생했습니다:\n{str(e)}')

    def collect_edited_table_data(self):
        """테이블에서 편집된 데이터를 수집"""
        try:
            # 결과 위젯에서 모든 테이블을 찾아서 편집된 내용 수집
            for i in range(self.result_layout.count()):
                scene_frame = self.result_layout.itemAt(i).widget()
                if scene_frame:
                    table_widget = None
                    for child in scene_frame.findChildren(QTableWidget):
                        table_widget = child
                        break

                    if table_widget and i < len(self.edited_scenes):
                        scene_data = self.edited_scenes[i]
                        scene_data['visual'] = table_widget.item(0, 1).text() if table_widget.item(0, 1) else ''
                        scene_data['audio'] = table_widget.item(1, 1).text() if table_widget.item(1, 1) else ''
                        scene_data['text'] = table_widget.item(2, 1).text() if table_widget.item(2, 1) else ''
                        scene_data['description'] = table_widget.item(3, 1).text() if table_widget.item(3, 1) else ''
        except Exception as e:
            print(f"테이블 데이터 수집 중 오류: {e}")

    def copy_images_to_folder(self):
        """생성된 이미지들을 프로젝트 폴더에 복사"""
        try:
            images_folder = os.path.join(self.current_project_folder, 'images')
            if not os.path.exists(images_folder):
                os.makedirs(images_folder)

            for scene_number, image_info in self.generated_images.items():
                if 'image_object' in image_info:
                    # PIL Image 객체를 파일로 저장
                    new_filename = f"scene_{scene_number}.png"
                    new_path = os.path.join(images_folder, new_filename)
                    image_info['image_object'].save(new_path, 'PNG')

                    # 저장 후 경로 정보 업데이트
                    self.generated_images[scene_number]['image_path'] = new_path

        except Exception as e:
            print(f"이미지 복사 중 오류: {e}")  # 로그만 출력, 사용자에게는 보이지 않음

    def get_button_style(self, color):
        """버튼 스타일 반환"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 10px 20px;
                border: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 12px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}bb;
            }}
            QPushButton:disabled {{
                background-color: #cccccc;
                color: #666666;
            }}
        """


if __name__ == "__main__":

   ### imagen4 테스트
    import json
    import glob
    import os
    from common.gemini import Gemini

    gemini = Gemini()
    json_file = glob.glob('./output/**/*.json')[0] ## json_path 직접 입력
    with open(json_file, 'r') as f:
        json_file = json.load(f)

    # Create temp folder if it doesn't exist
    temp_folder = './temp'
    os.makedirs(temp_folder, exist_ok=True)

    # Generate 8 scenes
    scenario = json_file['scenes']
    for data in scenario:
        prompt = f"""
        아래의 정보는 스토리보드의 주요 씬(장면)에 대한 내용이야. 해당 내용 참고하여 스토리보드 스케치 이미지 만들어줘
            **시각적 묘사**: {data['visual']},
            **음향 효과**: {data['audio']},
            **자막 또는 나레이션**: {data['text']},
            **장면 묘사** : {data['description']}
        """
        try:
            sketch_image = gemini._call_imagen_text(prompt)
            temp_path = os.path.join(temp_folder, f"scene_{data['scene_number']}.png")

            # Display and save image
            sketch_image.show()
            sketch_image.save(temp_path, 'PNG')

            print(f"Scene {data['scene_number']} saved to {temp_path}")

        except Exception as e:
            print(f"Error generating scene {data['scene_number']}: {e}")
            continue