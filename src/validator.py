import os
import json

from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QTextEdit, QGroupBox, QProgressBar, QMessageBox,
                             QHeaderView, QScrollArea, QWidget, QFrame)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QPixmap
from common.gemini import Gemini
from google.genai.types import Part


class ValidationThread(QThread):
    """스토리보드 검증을 위한 스레드"""
    scene_validated = pyqtSignal(int, dict)  # scene_number, validation_result
    validation_completed = pyqtSignal(list)  # all_results
    error_occurred = pyqtSignal(str)

    def __init__(self, scenes_data, temp_folder):
        super().__init__()
        self.scenes_data = scenes_data
        self.temp_folder = temp_folder
        self.gemini = Gemini()

    def run(self):
        try:
            validation_results = []

            for scene in self.scenes_data:
                scene_number = scene['scene_number']
                result = self.validate_scene(scene, scene_number)
                validation_results.append(result)
                self.scene_validated.emit(scene_number, result)

            self.validation_completed.emit(validation_results)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def validate_scene(self, scene_data, scene_number):
        """개별 씬 검증"""
        try:
            # 이미지 파일 경로 찾기
            image_path = os.path.join(self.temp_folder, f"scene_{scene_number}.png")

            # 이미지를 바이트로 읽기
            with open(image_path, 'rb') as f:
                img_bytes = f.read()
                image_part = Part.from_bytes(data=img_bytes, mime_type="image/png")

            # 검증 프롬프트 생성
            validation_prompt = self.create_validation_prompt(scene_data)
            contents = [validation_prompt, image_part]

            # Gemini API 호출
            response = self.gemini._call_gemini_multimodal(contents)

            # 응답 파싱
            result = self.parse_validation_response(response.text, scene_number)
            return result

        except Exception as e:
            return {
                'scene_number': scene_number,
                'total_score': 0,
                'scores': {'시각적 일치도': 0, '광고 적합성': 0, '메시지 전달력': 0},
                'reasons': {'시각적 일치도': f'오류: {str(e)}',
                            '광고 적합성': f'오류: {str(e)}',
                            '메시지 전달력': f'오류: {str(e)}'},
                'improvements': f'검증 중 오류가 발생했습니다: {str(e)}',
                'regeneration_prompt': ''
            }

    def create_validation_prompt(self, scene_data):
        """검증 프롬프트 생성"""
        return f"""
            이 이미지는 광고 스토리보드의 한 씬입니다. 아래 원본 스토리보드 정보와 비교하여 평가해주세요.
            
            **원본 스토리보드 정보:**
            - 화면 내용: {scene_data.get('visual', '')}
            - 음성/음향: {scene_data.get('audio', '')}
            - 자막/텍스트: {scene_data.get('text', '')}
            - 씬 설명: {scene_data.get('description', '')}
            - 분위기/무드: {scene_data.get('mood', '')}
            
            **평가 기준 (각 항목 0-5점):**
            1. 시각적 일치도: 원본 스토리보드의 화면 내용과 얼마나 일치하는가
            2. 광고 적합성: 광고 목적에 얼마나 적합한 이미지인가
            3. 메시지 전달력: 의도한 메시지가 얼마나 잘 전달되는가
            
            **응답 형식 (JSON):**
            {{
              "scores": {{
                "시각적 일치도": 점수(0-5),
                "광고 적합성": 점수(0-5),
                "메시지 전달력": 점수(0-5)
              }},
              "reasons": {{
                "시각적 일치도": "평가 이유",
                "광고 적합성": "평가 이유",
                "메시지 전달력": "평가 이유"
              }},
              "improvements": "구체적인 개선 방안",
              "regeneration_prompt": "이미지 재생성을 위한 수정된 프롬프트"
            }}
            
            위 형식에 맞춰 JSON으로만 응답해주세요.
            """

    def parse_validation_response(self, response_text, scene_number):
        """검증 응답 파싱"""
        try:
            # JSON 부분만 추출
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}') + 1

            if start_idx == -1 or end_idx == 0:
                raise ValueError("JSON 형식을 찾을 수 없습니다.")

            json_str = response_text[start_idx:end_idx]
            data = json.loads(json_str)

            # 총점 계산
            scores = data.get('scores', {})
            total_score = sum(scores.values()) / len(scores) if scores else 0

            return {
                'scene_number': scene_number,
                'total_score': round(total_score, 1),
                'scores': scores,
                'reasons': data.get('reasons', {}),
                'improvements': data.get('improvements', ''),
                'regeneration_prompt': data.get('regeneration_prompt', '')
            }

        except Exception as e:
            # 파싱 실패 시 기본값 반환
            return {
                'scene_number': scene_number,
                'total_score': 0,
                'scores': {'시각적 일치도': 0, '광고 적합성': 0, '메시지 전달력': 0},
                'reasons': {'시각적 일치도': '응답 파싱 실패',
                            '광고 적합성': '응답 파싱 실패',
                            '메시지 전달력': '응답 파싱 실패'},
                'improvements': f'응답 파싱 중 오류 발생: {str(e)}',
                'regeneration_prompt': ''
            }


class ValidationResultDialog(QDialog):
    """검증 결과를 표시하는 다이얼로그"""

    regenerate_requested = pyqtSignal(int, str)  # scene_number, improved_prompt

    def __init__(self, validation_results, parent=None):
        super().__init__(parent)
        self.validation_results = validation_results
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('스토리보드 검증 결과')
        self.setGeometry(100, 100, 500, 900)

        layout = QVBoxLayout()

        # 제목
        title_label = QLabel('스토리보드 검증 결과')
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 전체 점수 요약
        self.create_summary_section(layout)

        # 상세 결과 테이블
        self.create_detail_table(layout)

        # 개선사항 및 재생성 섹션
        self.create_improvement_section(layout)

        # 버튼
        button_layout = QHBoxLayout()
        close_button = QPushButton('닫기')
        close_button.clicked.connect(self.close)
        close_button.setStyleSheet(self.get_button_style('#757575'))
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def create_summary_section(self, layout):
        """전체 점수 요약 섹션"""
        summary_group = QGroupBox('전체 점수 요약')
        summary_layout = QHBoxLayout()

        # 평균 점수 계산
        total_scores = [result['total_score'] for result in self.validation_results]
        avg_score = sum(total_scores) / len(total_scores) if total_scores else 0

        # 점수별 개수
        excellent = len([s for s in total_scores if s >= 4.0])
        good = len([s for s in total_scores if 3.0 <= s < 4.0])
        poor = len([s for s in total_scores if s < 3.0])

        summary_text = f"""
        <div style="text-align: center; font-size: 14px;">
            <p><b>전체 평균 점수: {avg_score:.1f}/5.0</b></p>
            <p>우수 (4.0+): {excellent}씬 | 양호 (3.0+): {good}씬 | 개선필요 (3.0미만): {poor}씬</p>
        </div>
        """

        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 15px;
            }
        """)
        summary_layout.addWidget(summary_label)
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

    def create_detail_table(self, layout):
        """상세 결과 테이블"""
        table_group = QGroupBox('씬별 상세 점수')
        table_layout = QVBoxLayout()

        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(7)
        self.detail_table.setHorizontalHeaderLabels([
            '씬', '시각적 일치도', '광고 적합성', '메시지 전달력', '총점', '주요 이슈', '재생성'
        ])

        # 테이블 스타일
        self.detail_table.setStyleSheet("""
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }
            QHeaderView::section {
                background-color: #f8f9fa;
                padding: 10px;
                border: 1px solid #dee2e6;
                font-weight: bold;
            }
        """)

        # 테이블 데이터 채우기
        self.populate_table()

        # 컬럼 너비 조정
        header = self.detail_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Fixed)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.Fixed)
        self.detail_table.setColumnWidth(0, 50)
        self.detail_table.setColumnWidth(1, 100)
        self.detail_table.setColumnWidth(2, 100)
        self.detail_table.setColumnWidth(3, 100)
        self.detail_table.setColumnWidth(4, 80)
        self.detail_table.setColumnWidth(6, 100)

        table_layout.addWidget(self.detail_table)
        table_group.setLayout(table_layout)
        layout.addWidget(table_group)

    def populate_table(self):
        """테이블에 데이터 채우기"""
        self.detail_table.setRowCount(len(self.validation_results))

        for row, result in enumerate(self.validation_results):
            # 씬 번호
            self.detail_table.setItem(row, 0, QTableWidgetItem(f"#{result['scene_number']}"))

            # 각 점수
            scores = result['scores']
            self.detail_table.setItem(row, 1, QTableWidgetItem(str(scores.get('시각적 일치도', 0))))
            self.detail_table.setItem(row, 2, QTableWidgetItem(str(scores.get('광고 적합성', 0))))
            self.detail_table.setItem(row, 3, QTableWidgetItem(str(scores.get('메시지 전달력', 0))))

            # 총점 (색상 적용)
            total_item = QTableWidgetItem(str(result['total_score']))
            if result['total_score'] >= 4.0:
                total_item.setBackground(Qt.green)
            elif result['total_score'] >= 3.0:
                total_item.setBackground(Qt.yellow)
            else:
                total_item.setBackground(Qt.red)
            self.detail_table.setItem(row, 4, total_item)

            # 주요 이슈 (가장 낮은 점수의 이유)
            reasons = result['reasons']
            min_score_key = min(scores.keys(), key=lambda k: scores[k])
            main_issue = f"{min_score_key}: {reasons.get(min_score_key, '')}"
            self.detail_table.setItem(row, 5, QTableWidgetItem(main_issue))

            # 재생성 버튼
            if result['total_score'] < 4.0:  # 4점 미만인 경우만 재생성 버튼 활성화
                regen_button = QPushButton('재생성')
                regen_button.setStyleSheet(self.get_button_style('#dc3545'))
                regen_button.clicked.connect(
                    lambda checked, sn=result['scene_number'], prompt=result['regeneration_prompt']:
                    self.regenerate_scene(sn, prompt)
                )
                self.detail_table.setCellWidget(row, 6, regen_button)

    def create_improvement_section(self, layout):
        """개선사항 섹션"""
        improvement_group = QGroupBox('개선사항 및 권장사항')
        improvement_layout = QVBoxLayout()

        scroll_area = QScrollArea()
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)

        for result in self.validation_results:
            if result['total_score'] < 4.0:  # 개선이 필요한 씬만 표시
                scene_frame = QFrame()
                scene_frame.setStyleSheet("""
                    QFrame {
                        background-color: #fff3cd;
                        border: 1px solid #ffeaa7;
                        border-radius: 5px;
                        margin: 5px;
                        padding: 10px;
                    }
                """)

                scene_layout = QVBoxLayout(scene_frame)

                # 씬 제목
                title_label = QLabel(f"Scene #{result['scene_number']} (점수: {result['total_score']}/5.0)")
                title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
                scene_layout.addWidget(title_label)

                # 개선사항
                improvement_text = QTextEdit()
                improvement_text.setPlainText(result['improvements'])
                improvement_text.setMaximumHeight(80)
                improvement_text.setReadOnly(True)
                scene_layout.addWidget(improvement_text)

                scroll_layout.addWidget(scene_frame)

        scroll_area.setWidget(scroll_widget)
        scroll_area.setWidgetResizable(True)
        scroll_area.setMaximumHeight(200)

        improvement_layout.addWidget(scroll_area)
        improvement_group.setLayout(improvement_layout)
        layout.addWidget(improvement_group)

    def regenerate_scene(self, scene_number, improved_prompt):
        """씬 재생성 요청"""
        reply = QMessageBox.question(
            self, '이미지 재생성',
            f'Scene #{scene_number}의 이미지를 개선된 프롬프트로 재생성하시겠습니까?',
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            self.regenerate_requested.emit(scene_number, improved_prompt)
            QMessageBox.information(self, '재생성 요청',
                                    f'Scene #{scene_number}의 이미지 재생성을 요청했습니다.')
            self.close()

    def get_button_style(self, color):
        """버튼 스타일 반환"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                padding: 8px 16px;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {color}dd;
            }}
        """


class StoryboardValidator:
    """스토리보드 검증 메인 클래스"""

    def __init__(self, parent_dialog):
        self.parent_dialog = parent_dialog
        self.temp_folder = './temp'

    def validate_storyboard(self, scenes_data):
        """스토리보드 검증 시작"""
        try:
            # 검증 다이얼로그 생성
            validation_dialog = QDialog(self.parent_dialog)
            validation_dialog.setWindowTitle('스토리보드 검증 중...')
            validation_dialog.setGeometry(200, 200, 400, 150)

            layout = QVBoxLayout()

            # 진행 상황 표시
            progress_label = QLabel('스토리보드를 검증하고 있습니다...')
            progress_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(progress_label)

            progress_bar = QProgressBar()
            progress_bar.setRange(0, len(scenes_data))
            progress_bar.setValue(0)
            layout.addWidget(progress_bar)

            status_label = QLabel('검증 준비 중...')
            status_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(status_label)

            validation_dialog.setLayout(layout)
            validation_dialog.show()

            # 검증 스레드 시작
            validation_thread = ValidationThread(scenes_data, self.temp_folder)

            def on_scene_validated(scene_number, result):
                progress_bar.setValue(progress_bar.value() + 1)
                status_label.setText(f'Scene #{scene_number} 검증 완료')

            def on_validation_completed(results):
                validation_dialog.close()
                self.show_validation_results(results)

            def on_error(error_msg):
                validation_dialog.close()
                QMessageBox.critical(self.parent_dialog, '검증 오류',
                                     f'검증 중 오류가 발생했습니다:\n{error_msg}')

            validation_thread.scene_validated.connect(on_scene_validated)
            validation_thread.validation_completed.connect(on_validation_completed)
            validation_thread.error_occurred.connect(on_error)
            validation_thread.start()

        except Exception as e:
            QMessageBox.critical(self.parent_dialog, '검증 시작 오류',
                                 f'검증을 시작할 수 없습니다:\n{str(e)}')

    def show_validation_results(self, validation_results):
        """검증 결과 표시"""
        result_dialog = ValidationResultDialog(validation_results, self.parent_dialog)

        # 재생성 요청 처리
        result_dialog.regenerate_requested.connect(self.handle_regeneration_request)

        result_dialog.exec_()

    def handle_regeneration_request(self, scene_number, improved_prompt):
        """재생성 요청 처리"""
        # 부모 다이얼로그의 재생성 메서드 호출
        if hasattr(self.parent_dialog, 'regenerate_scene_with_prompt'):
            self.parent_dialog.regenerate_scene_with_prompt(scene_number, improved_prompt)
        else:
            QMessageBox.information(self.parent_dialog, '알림', '재생성 기능이 아직 구현되지 않았습니다.')


# ## 줄거리 plot
# class PlotGenerator:
#     """각 씬에 대한 이미지로부터 검증용 줄거리 생성"""
#
#     def __init__(self):
#         from common.gemini import Gemini
#         self.gemini = Gemini()
#         self.temp_folder = './temp'
#
#     def run(self):
#         """이미지들로부터 전체 줄거리 생성"""
#         image_files = []
#
#         # temp 폴더에서 scene_ 이미지 파일들 찾기
#         if not os.path.exists(self.temp_folder):
#             raise Exception(f"temp 폴더 '{self.temp_folder}'가 존재하지 않습니다.")
#
#         for f_name in os.listdir(self.temp_folder):
#             if f_name.startswith('scene_') and f_name.endswith('.png'):
#                 try:
#                     # 파일명에서 숫자 부분 추출 (예: scene_1.png -> 1)
#                     suffix_part = f_name.split('_')[-1].split('.')[0]
#                     image_number = int(suffix_part)
#                     image_files.append((image_number, os.path.join(self.temp_folder, f_name)))
#                 except ValueError:
#                     continue  # 숫자가 아닌 경우 건너뛰기
#
#         # 파일명 접미사 번호순으로 정렬
#         image_files.sort(key=lambda x: x[0])
#
#         if len(image_files) == 0:
#             raise Exception("이미지 파일을 찾을 수 없습니다. 파일명과 경로를 확인해주세요.")
#
#         if len(image_files) != 8:
#             print(f"경고: '{self.temp_folder}' 폴더에 8개의 이미지가 발견되지 않았습니다. 현재 {len(image_files)}개.")
#
#         # 로컬에 저장된 이미지 bytes 형식으로 변환하기
#         contents = []
#         for image_file in image_files:
#             try:
#                 with open(image_file[1], 'rb') as f:
#                     img_bytes = f.read()
#                     from google.genai.types import Part
#                     contents.append(Part.from_bytes(data=img_bytes, mime_type="image/png"))
#             except Exception as e:
#                 print(f"이미지 로드 실패 {image_file[1]}: {e}")
#                 continue
#
#         if not contents:
#             raise Exception("유효한 이미지를 로드할 수 없습니다.")
#
#         # 줄거리 생성 프롬프트
#         prompt = """
#         이 이미지들은 하나의 광고 스토리보드를 구성하는 연속된 씬들입니다.
#         각 이미지의 순서에 따라 전체적인 줄거리를 2~3줄 분량으로 작성해 주세요.
#
#         다음 요소들을 포함해서 작성해주세요:
#         1. 광고의 주요 메시지나 컨셉
#         2. 씬들 간의 연결성과 흐름
#         3. 타겟 고객에게 전달하려는 핵심 내용
#
#         형식: 간결하고 명확한 2-3문장으로 작성
#         """
#
#         contents.insert(0, prompt)
#
#         try:
#             response = self.gemini._call_gemini_multimodal(contents)
#             return response.text
#         except Exception as e:
#             raise Exception(f"Gemini API 호출 실패: {e}")
#
#     def generate_scene_description(self, image_path):
#         """개별 씬 이미지에 대한 설명 생성"""
#         try:
#             with open(image_path, 'rb') as f:
#                 img_bytes = f.read()
#                 from google.genai.types import Part
#                 image_part = Part.from_bytes(data=img_bytes, mime_type="image/png")
#
#             prompt = """
#             이 이미지는 광고 스토리보드의 한 씬입니다.
#             다음 관점에서 이미지를 분석하고 설명해주세요:
#
#             1. 화면 구성: 인물, 배경, 소품 등의 배치
#             2. 시각적 요소: 색감, 조명, 분위기
#             3. 전달되는 메시지: 이 씬이 전달하고자 하는 내용
#             4. 광고 효과: 광고 목적에 어떻게 기여하는지
#
#             간결하고 구체적으로 작성해주세요.
#             """
#
#             contents = [prompt, image_part]
#             response = self.gemini._call_gemini_multimodal(contents)
#             return response.text
#
#         except Exception as e:
#             return f"이미지 분석 실패: {str(e)}"
#
