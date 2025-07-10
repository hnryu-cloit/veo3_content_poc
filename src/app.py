import sys
import json
from PyQt5.QtWidgets import (QApplication, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QTextEdit, QComboBox, QPushButton,
                             QScrollArea, QFrame, QMessageBox, QGroupBox, QFileDialog,
                             QProgressBar, QInputDialog)
from PyQt5.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt5.QtSvg import QSvgRenderer
from PyQt5.QtGui import QIcon, QPixmap, QPainter,QFont
from common.gemini import Gemini
from common.prompt import AppPrompt
from storyboard import StoryboardDialog
import os



class ApiThread(QThread):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

    def __init__(self, form_data):
        super().__init__()
        self.form_data = form_data

    def run(self):
        try:
            gemini = Gemini()
            # 전체 plot 생성
            prompt = self.create_plot_prompt(self.form_data)
            response = gemini._call_gemini_text(prompt)

            # plot 기반 scene description 생성
            prompt = self.create_storyboard_prompt(self.form_data, response)
            response = gemini._call_gemini_text(prompt)
            print(response)

            # 스트림 응답 처리
            storyboards = json.loads(response)
            try:
                self.finished.emit(storyboards)
            except json.JSONDecodeError:
                self.finished.emit({"raw_response": response})

        except Exception as e:
            self.error.emit(str(e))

    def create_plot_prompt(self, data):
        """폼 데이터를 기반으로 프롬프트 생성"""
        prompt = f"""
        아래의 [제품/광고목적/타겟]에 대한 광고 콘티에 대한 plot을 2~3줄 분량으로 작성해주세요.

        제품명: {data['product_name']}
        제품 설명: {data['product_description']}
        톤 앤 매너: {data['tone_manner']}
        """
        return prompt

    def create_storyboard_prompt(self, data, response):
        """폼 데이터를 기반으로 프롬프트 생성"""
        prompt = f"""
        광고 plot: {response}
        제품명: {data['product_name']}
        제품 설명: {data['product_description']}
        톤 앤 매너: {data['tone_manner']}
        """

        if not data['reference_files'] is None:
            prompt += f"참고할 파일들: "
            for i, file_info in enumerate(data['reference_files'], 1):
                prompt += f"{i}. {file_info['파일설명']}: {file_info['파일명']}\n"

        prompt += """
        - 위에서 입력받은 광고 plot 정보와 사용자 입력 기반으로 다음 JSON 구조에 맞춰 광고 스토리보드를 생성해 주세요.
        - 스토리보드 전체 길이는 8초이며 스토리보드 내 8개의 scene이 존재하며 각 scene의 길이는 1초입니다.
        ** 출력 형식 **
        {
          "storyboard1":{
            "title": "광고 제목",
            "total duration": "전체 광고 길이",
            "plot": [광고 plot],
            "mood": [톤 앤 매너],
            "scenes": [
              {
                    "scene_number": 1,
                    "duration": "씬 길이",
                    "visual": "인물 배치, 카메라 앵글, 배경 설정(실내/실외, 구체적 장소), 화면 전환 효과",
                    "audio": "나레이션, 배경 음악, 효과 음악에 대한 설명(레퍼런스)",
                    "text": "영상의 내용이나 대사를 담는 자막 또는 캡션",
                    "description": "씬의 설명"
                  },
                  {
                    "scene_number": 2,
                    "duration": "씬 길이",
                    "visual": "인물 배치, 카메라 앵글, 배경 설정(실내/실외, 구체적 장소), 화면 전환 효과",
                    "audio": "나레이션, 배경 음악, 효과 음악에 대한 설명(레퍼런스)",
                    "text": "영상의 내용이나 대사를 담는 자막 또는 캡션",
                    "description": "씬의 설명"
                  },
                  ....,
                  {
                    "scene_number": 8,
                    "duration": "씬 길이",
                    "visual": "인물 배치, 카메라 앵글, 배경 설정(실내/실외, 구체적 장소), 화면 전환 효과",
                    "audio": "나레이션, 배경 음악, 효과 음악에 대한 설명(레퍼런스)",
                    "text": "영상의 내용이나 대사를 담는 자막 또는 캡션",
                    "description": "씬의 설명"
                  },
                ],
                "key_messages": ["핵심 메시지 1", "핵심 메시지 2"],
                "call_to_action": "행동 유도 문구"
              }
            }
        """

        return prompt


class AdContentForm(QWidget):
    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        # self.setWindowTitle('pTBWA-PoC: CLOIT - 광고 콘텐츠 생성')
        self.setGeometry(100, 100, 500, 550)

        # 메인 레이아웃
        main_layout = QVBoxLayout()

        # 스크롤 영역 생성
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        # 제목
        title_label = QLabel('광고 콘텐츠 생성')
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        scroll_layout.addWidget(title_label)

        # 구분선
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        scroll_layout.addWidget(line)

        # 1. 제품명 및 설명
        product_group = QGroupBox('제품명 및 설명')
        product_group.setFixedHeight(200)
        product_layout = QVBoxLayout()

        product_layout.addWidget(QLabel('제품명:'))
        self.product_name = QLineEdit()
        self.product_name.setPlaceholderText('제품명을 입력하세요')
        product_layout.addWidget(self.product_name)

        product_layout.addWidget(QLabel('제품 설명:'))
        self.product_description = QTextEdit()
        self.product_description.setPlaceholderText('제품에 대한 상세 설명을 입력하세요')
        self.product_description.setMaximumHeight(80)
        product_layout.addWidget(self.product_description)

        product_group.setLayout(product_layout)
        scroll_layout.addWidget(product_group)

        ## 중간 평가 제외 항목
        # # 2. 콘텐츠 목적
        # purpose_group = QGroupBox('콘텐츠 목적')
        # purpose_layout = QVBoxLayout()
        #
        # self.content_purpose = QComboBox()
        # self.content_purpose.addItems([
        #     '선택하세요',
        #     '신제품 출시',
        #     '이벤트 안내',
        #     '브랜드 스토리 공유',
        #     '사용팁',
        #     '제품 리뷰',
        #     '기타'
        # ])
        # self.content_purpose.setEditable(True)
        # purpose_layout.addWidget(self.content_purpose)
        #
        # purpose_group.setLayout(purpose_layout)
        # scroll_layout.addWidget(purpose_group)
        #
        # # 3. 핵심 메시지
        # message_group = QGroupBox('핵심 메시지')
        # message_layout = QVBoxLayout()
        #
        # self.core_message = QTextEdit()
        # self.core_message.setPlaceholderText('광고를 통해 전달하고자 하는 핵심 메시지를 입력하세요')
        # self.core_message.setMaximumHeight(80)
        # message_layout.addWidget(self.core_message)
        #
        # message_group.setLayout(message_layout)
        # message_group.setMaximumHeight(100)
        # scroll_layout.addWidget(message_group)
        #
        # # 4. 광고 채널
        # channel_group = QGroupBox('광고 채널')
        # channel_layout = QVBoxLayout()
        #
        # self.ad_channel = QComboBox()
        # self.ad_channel.addItems([
        #     '선택하세요',
        #     '유튜브',
        #     '인스타그램',
        #     '페이스북',
        #     'TV광고',
        #     '기업 자사 홈페이지',
        #     '네이버 블로그',
        #     '카카오톡',
        #     '기타'
        # ])
        # self.ad_channel.setEditable(True)
        # channel_layout.addWidget(self.ad_channel)
        #
        # channel_group.setLayout(channel_layout)
        # scroll_layout.addWidget(channel_group)
        #
        # # 5. 타겟 고객
        # target_group = QGroupBox('타겟 고객')
        # target_layout = QVBoxLayout()
        #
        # self.target_customer = QTextEdit()
        # self.target_customer.setPlaceholderText('타겟 고객을 구체적으로 설명해 주세요 (연령대, 성별, 관심사 등)')
        # self.target_customer.setMaximumHeight(80)
        # target_layout.addWidget(self.target_customer)
        #
        # target_group.setLayout(target_layout)
        # target_group.setMaximumHeight(100)
        # scroll_layout.addWidget(target_group)

        # 6. 톤앤매너

        tone_group = QGroupBox('톤앤매너')
        tone_layout = QVBoxLayout()

        self.tone_manner = QComboBox()
        self.tone_manner.addItems([
            '선택하세요',
            '친근하고 캐주얼한',
            '전문적이고 신뢰감 있는',
            '젊고 트렌디한',
            '고급스럽고 세련된',
            '따뜻하고 감성적인',
            '유머러스하고 재미있는',
            '기타'
        ])
        self.tone_manner.setEditable(True)
        tone_layout.addWidget(self.tone_manner)

        tone_group.setLayout(tone_layout)
        scroll_layout.addWidget(tone_group)

        # 7. 참고용 데이터
        reference_group = QGroupBox('참고용 데이터')
        reference_layout = QVBoxLayout()

        # 파일 리스트를 저장할 리스트 초기화
        self.reference_files = []

        # 파일 목록을 표시할 위젯
        self.files_layout = QVBoxLayout()
        reference_layout.addLayout(self.files_layout)

        # 파일 추가 버튼
        add_file_layout = QHBoxLayout()
        add_file_layout.addStretch()
        self.add_file_button = QPushButton('+ 참고용 파일 추가')
        self.add_file_button.clicked.connect(self.add_reference_file)
        self.add_file_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        add_file_layout.addWidget(self.add_file_button)
        reference_layout.addLayout(add_file_layout)

        reference_group.setLayout(reference_layout)
        scroll_layout.addWidget(reference_group)

        # 스크롤 영역 설정
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        main_layout.addWidget(scroll)

        # 버튼 영역
        button_layout = QHBoxLayout()

        self.clear_button = QPushButton('초기화')
        self.clear_button.clicked.connect(self.clear_form)
        button_layout.addWidget(self.clear_button)

        button_layout.addStretch()

        self.generate_button = QPushButton('스토리보드 생성')
        self.generate_button.clicked.connect(self.generate_storyboard)
        self.generate_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 7px;
                border: none;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        button_layout.addWidget(self.generate_button)
        main_layout.addLayout(button_layout)

        # 프로그레스 바
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        self.setLayout(main_layout)

    def clear_form(self):
        """폼 초기화"""
        self.product_name.clear()
        self.product_description.clear()
        # self.content_purpose.setCurrentIndex(0)
        # self.core_message.clear()
        # self.ad_channel.setCurrentIndex(0)
        # self.target_customer.clear()
        self.tone_manner.setCurrentIndex(0)
        # 참고용 파일들 초기화
        self.clear_reference_files()

    def clear_reference_files(self):
        """참고용 파일 목록 초기화"""
        for file_widget in self.reference_files:
            file_widget['widget'].setParent(None)
        self.reference_files.clear()

    def add_reference_file(self):
        """참고용 파일 추가"""
        file_index = len(self.reference_files)

        # 파일 위젯 컨테이너
        file_widget = QFrame()
        file_widget.setFrameStyle(QFrame.Box)
        file_widget.setStyleSheet("QFrame { border: 1px solid #ccc; border-radius: 4px; padding: 5px; margin: 2px; }")

        file_layout = QVBoxLayout(file_widget)

        # 파일 이름 입력
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel('파일 설명:'))
        file_name_input = QLineEdit()
        file_name_input.setPlaceholderText('예: 제품 카탈로그, 서비스 소개서, 홍보 기획안 등')
        name_layout.addWidget(file_name_input)
        file_layout.addLayout(name_layout)

        # 파일 선택
        path_layout = QHBoxLayout()
        file_path_input = QLineEdit()
        file_path_input.setPlaceholderText('PDF 파일을 선택하세요')
        file_path_input.setReadOnly(True)
        path_layout.addWidget(file_path_input)

        select_button = QPushButton('파일 선택')
        select_button.clicked.connect(lambda: self.select_file(file_path_input))
        path_layout.addWidget(select_button)

        remove_button = QPushButton('삭제')
        remove_button.clicked.connect(lambda: self.remove_reference_file(file_index))
        remove_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                padding: 5px 10px;
                border: none;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
        """)
        path_layout.addWidget(remove_button)
        file_layout.addLayout(path_layout)

        # 파일 정보 저장
        file_info = {
            'widget': file_widget,
            'name_input': file_name_input,
            'path_input': file_path_input,
            'index': file_index
        }

        self.reference_files.append(file_info)
        self.files_layout.addWidget(file_widget)

    def remove_reference_file(self, file_index):
        """참고용 파일 삭제"""
        for i, file_info in enumerate(self.reference_files):
            if file_info['index'] == file_index:
                # 위젯 삭제
                file_info['widget'].setParent(None)
                # 리스트에서 제거
                self.reference_files.pop(i)
                break

    def select_file(self, path_widget):
        """PDF 파일 선택"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            'PDF 파일 선택',
            '',
            'PDF Files (*.pdf);;All Files (*)'
        )

        if file_path:
            path_widget.setText(file_path)

    def get_file_info(self, file_path):
        """파일 정보 반환"""
        if file_path and os.path.exists(file_path):
            file_name = os.path.basename(file_path)
            file_size = os.path.getsize(file_path)
            return {
                "파일명": file_name,
                "파일경로": file_path,
                "파일크기": f"{file_size / 1024:.1f} KB"
            }
        return None

    def get_all_reference_files(self):
        """모든 참고용 파일 정보 반환"""
        files_data = []
        for file_info in self.reference_files:
            file_path = file_info['path_input'].text().strip()
            file_description = file_info['name_input'].text().strip()

            if file_path:  # 파일이 선택된 경우만
                file_data = self.get_file_info(file_path)
                if file_data:
                    file_data["파일설명"] = file_description if file_description else "설명 없음"
                    files_data.append(file_data)

        return files_data

    def validate_form(self):
        """폼 유효성 검사"""
        if not self.product_name.text().strip():
            QMessageBox.warning(self, '입력 오류', '제품명을 입력해주세요.')
            return False

        if not self.product_description.toPlainText().strip():
            QMessageBox.warning(self, '입력 오류', '제품 설명을 입력해주세요.')
            return False

        if not self.tone_manner.currentText().strip() or self.tone_manner.currentText() == "선택하세요":
            QMessageBox.warning(self, '입력 오류', '톤 앤 매너를 선택해 주세요.')
            return False

        return True

    def generate_storyboard(self):
        """스토리보드 생성"""
        # 폼 유효성 검사
        if not self.validate_form():
            return

        # 폼 데이터 수집
        form_data = {
            "product_name": self.product_name.text().strip(),
            "product_description": self.product_description.toPlainText().strip(),
            # "content_purpose": self.content_purpose.currentText(),
            # "core_message": self.core_message.toPlainText().strip(),
            # "ad_channel": self.ad_channel.currentText(),
            # "target_customer": self.target_customer.toPlainText().strip(),
            "tone_manner": self.tone_manner.currentText(),
            "reference_files": self.get_all_reference_files()
        }

        # 프로그레스 바 표시
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.generate_button.setEnabled(False)
        self.generate_button.setText('생성 중...')

        # API 호출 스레드 시작
        self.gemini = ApiThread(form_data)
        self.gemini.finished.connect(self.on_storyboard_generated)
        self.gemini.error.connect(self.on_api_error)
        self.gemini.start()

    def on_storyboard_generated(self, storyboard_data):
        """스토리보드 생성 완료 처리"""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.generate_button.setText("스토리보드 생성")

        # 스토리보드 결과 다이얼로그 표시
        dialog = StoryboardDialog(storyboard_data, self)
        dialog.exec_()

    def on_api_error(self, error_message):
        """API 오류 처리"""
        self.progress_bar.setVisible(False)
        self.generate_button.setEnabled(True)
        self.generate_button.setText("스토리보드 생성")

        QMessageBox.critical(self, 'API 오류', f"스토리보드 생성 중 오류가 발생했습니다.:\n{error_message}")


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = AdContentForm()
    window.show()

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()