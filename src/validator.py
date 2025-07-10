import os
import json
import cv2

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

            if not os.path.exists(image_path):
                raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {image_path}")

            # 1단계: 이미지에서 실제 장면 설명 추출
            predicted_description = self.extract_scene_description(image_path)

            # 2단계: 원본 설명과 추출된 설명 비교 평가
            validation_result = self.compare_descriptions(scene_data, predicted_description, scene_number)

            return validation_result

        except Exception as e:
            return {
                'scene_number': scene_number,
                'total_score': 0,
                'scores': {'메시지 전달력': 0, '창의성 및 독창성': 0, '브랜드/제품 적합성': 0},
                'reasons': {'메시지 전달력': f'오류: {str(e)}',
                            '창의성 및 독창성': f'오류: {str(e)}',
                            '브랜드/제품 적합성': f'오류: {str(e)}'},
                'improvements': f'검증 중 오류가 발생했습니다: {str(e)}',
                'regeneration_prompt': '',
                'predicted_description': '추출 실패'
            }

    def extract_scene_description(self, image_path):
        """이미지에서 실제 장면 설명 추출"""
        try:
            # OpenCV로 이미지 읽기
            image = cv2.imread(image_path)
            success, encoded_image = cv2.imencode('.png', image)
            img_bytes = encoded_image.tobytes()

            # 이미지 분석 프롬프트
            prompt = """
            입력받은 scene 이미지는 광고 영상 중 일부 장면에 대한 이미지입니다.
            이미지를 보고 해당 scene에 해당하는 설명을 한 문장으로 작성해주세요.
            부분적인 묘사보다는 핵심 스토리에 대해 작성해주세요.

            출력 예시: {
            "scene_description": "윤기가 흐르는 닭강정과 반숙란이 담긴 접시가 식욕을 자극하는 광고 영상의 한 장면입니다."
            }
            """

            contents = [prompt, Part.from_bytes(data=img_bytes, mime_type="image/png")]
            response = self.gemini._call_gemini_multimodal(contents)

            # JSON 파싱
            try:
                result = json.loads(response.text)
                return result.get("scene_description", "설명 추출 실패")
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트에서 추출 시도
                return response.text.strip()

        except Exception as e:
            return f"이미지 분석 실패: {str(e)}"

    def compare_descriptions(self, scene_data, predicted_description, scene_number):
        """원본 설명과 추출된 설명 비교"""
        try:
            # 원본 설명
            original_description = scene_data.get('description', '')

            score_prompt = f"""
            다음 동일 광고 scene에 대한 description에 대해 비교하려고 합니다.
            - 원본 설명: {original_description}
            - 검증용 설명: {predicted_description}
            다음 세 가지 기준에 따라 각각 0~5점(0: 전혀 유사하지 않음, 5: 매우 유사함)으로 평가하세요.
            1. 메시지 전달력: 광고의 핵심 메시지가 스케치에서 명확하게 시각적으로 표현되어 있는가?
            2. 창의성 및 독창성: 스케치가 기존 광고와 차별화되는 창의적 아이디어와 표현 방식을 보여주는가?
            3. 브랜드/제품 적합성: 스케치가 브랜드의 정체성, 제품 특성, 타깃 소비자와 잘 부합하는가?
            세 기준의 점수를 기반으로 전체 비교 총점을 산출하고 각 항목별로 간단한 평가 이유와 개선점을 작성하세요.
            아래의 JSON 형식으로 출력해주세요:

            {{
                "메시지 전달력": {{
                    "점수": 0~5,
                    "평가 이유": "설명",
                    "개선점": "설명"
                }},
                "창의성 및 독창성": {{
                    "점수": 0~5,
                    "평가 이유": "설명",
                    "개선점": "설명"
                }},
                "브랜드/제품 적합성": {{
                    "점수": 0~5,
                    "평가 이유": "설명",
                    "개선점": "설명"
                }},
            }}
            """

            response = self.gemini._call_gemini_text(score_prompt)

            # JSON 파싱
            try:
                result = json.loads(response)

                # UI 표시를 위한 형식으로 변환
                scores = {
                    '메시지 전달력': result.get('메시지 전달력', {}).get('점수', 0),
                    '창의성 및 독창성': result.get('창의성 및 독창성', {}).get('점수', 0),
                    '브랜드/제품 적합성': result.get('브랜드/제품 적합성', {}).get('점수', 0)
                }

                reasons = {
                    '메시지 전달력': result.get('메시지 전달력', {}).get('평가 이유', ''),
                    '창의성 및 독창성': result.get('창의성 및 독창성', {}).get('평가 이유', ''),
                    '브랜드/제품 적합성': result.get('브랜드/제품 적합성', {}).get('평가 이유', '')
                }

                improvements = []
                for key in ['메시지 전달력', '창의성 및 독창성', '브랜드/제품 적합성']:
                    improvement = result.get(key, {}).get('개선점', '')
                    if improvement:
                        improvements.append(f"{key}: {improvement}")

                improvements_text = " | ".join(improvements) if improvements else "개선사항 없음"

                # 총점 계산
                total_score = result.get('총점', 0)
                if total_score == 0:  # 총점이 없으면 평균 계산
                    total_score = sum(scores.values()) / len(scores) if scores else 0

                # 재생성 프롬프트 생성
                regeneration_prompt = f"""
                원본 설명: {original_description}
                추출된 설명: {predicted_description}

                개선사항:
                {improvements_text}

                위 개선사항을 반영하여 더 나은 이미지를 생성해주세요.
                """

                return {
                    'scene_number': scene_number,
                    'total_score': round(total_score, 1),
                    'scores': scores,
                    'reasons': reasons,
                    'improvements': improvements_text,
                    'regeneration_prompt': regeneration_prompt,
                    'predicted_description': predicted_description
                }

            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트에서 추출 시도
                return self.parse_text_response(response, scene_number, predicted_description)

        except Exception as e:
            return {
                'scene_number': scene_number,
                'total_score': 0,
                'scores': {'메시지 전달력': 0, '창의성 및 독창성': 0, '브랜드/제품 적합성': 0},
                'reasons': {'메시지 전달력': f'비교 분석 실패: {str(e)}',
                            '창의성 및 독창성': f'비교 분석 실패: {str(e)}',
                            '브랜드/제품 적합성': f'비교 분석 실패: {str(e)}'},
                'improvements': f'검증 중 오류가 발생했습니다: {str(e)}',
                'regeneration_prompt': '',
                'predicted_description': predicted_description
            }

    def parse_text_response(self, response_text, scene_number, predicted_description):
        """텍스트 응답에서 점수 추출 시도"""
        try:
            # 기본값 설정
            scores = {'메시지 전달력': 0, '창의성 및 독창성': 0, '브랜드/제품 적합성': 0}
            reasons = {'메시지 전달력': '파싱 실패', '창의성 및 독창성': '파싱 실패', '브랜드/제품 적합성': '파싱 실패'}

            # 간단한 점수 추출 시도
            lines = response_text.split('\n')
            for line in lines:
                if '메시지 전달력' in line and '점수' in line:
                    try:
                        score = int(''.join(filter(str.isdigit, line)))
                        scores['메시지 전달력'] = min(score, 5)
                    except:
                        pass
                elif '창의성' in line and '점수' in line:
                    try:
                        score = int(''.join(filter(str.isdigit, line)))
                        scores['창의성 및 독창성'] = min(score, 5)
                    except:
                        pass
                elif '브랜드' in line and '점수' in line:
                    try:
                        score = int(''.join(filter(str.isdigit, line)))
                        scores['브랜드/제품 적합성'] = min(score, 5)
                    except:
                        pass

            total_score = sum(scores.values()) / len(scores) if scores else 0

            return {
                'scene_number': scene_number,
                'total_score': round(total_score, 1),
                'scores': scores,
                'reasons': reasons,
                'improvements': '텍스트 파싱으로 추출된 결과입니다.',
                'regeneration_prompt': f'Scene {scene_number}을 개선해주세요.',
                'predicted_description': predicted_description
            }

        except Exception as e:
            return {
                'scene_number': scene_number,
                'total_score': 0,
                'scores': {'메시지 전달력': 0, '창의성 및 독창성': 0, '브랜드/제품 적합성': 0},
                'reasons': {'메시지 전달력': f'파싱 실패: {str(e)}',
                            '창의성 및 독창성': f'파싱 실패: {str(e)}',
                            '브랜드/제품 적합성': f'파싱 실패: {str(e)}'},
                'improvements': f'파싱 중 오류가 발생했습니다: {str(e)}',
                'regeneration_prompt': '',
                'predicted_description': predicted_description
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
        <div style="text-align: center; font-size: 13px;">
            <p><b>전체 평균 점수: {avg_score:.1f}/5.0</b></p>
            <p>우수 (4.0+): {excellent}Scene | 양호 (3.0+): {good}Scene | 개선 필요 (3.0미만): {poor}Scene</p>
        </div>
        """

        summary_label = QLabel(summary_text)
        summary_label.setStyleSheet("""
            QLabel {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 1px;
                padding: 10px;
            }
        """)
        summary_layout.addWidget(summary_label)
        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)

    def create_detail_table(self, layout):
        """상세 결과 테이블"""
        table_group = QGroupBox('Scene 별 상세 점수')
        table_layout = QVBoxLayout()

        self.detail_table = QTableWidget()
        self.detail_table.setColumnCount(8)
        self.detail_table.setHorizontalHeaderLabels([
            'Scene', '메시지 전달력', '창의성 및 독창성', '브랜드/제품 적합성', '총점', '추출된 설명', '주요 이슈', '재생성'
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
        header.setSectionResizeMode(5, QHeaderView.Stretch)  # 추출된 설명 컬럼
        header.setSectionResizeMode(6, QHeaderView.Stretch)  # 주요 이슈 컬럼
        header.setSectionResizeMode(7, QHeaderView.Fixed)
        self.detail_table.setColumnWidth(0, 50)
        self.detail_table.setColumnWidth(1, 100)
        self.detail_table.setColumnWidth(2, 100)
        self.detail_table.setColumnWidth(3, 100)
        self.detail_table.setColumnWidth(4, 80)
        self.detail_table.setColumnWidth(7, 100)

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
            self.detail_table.setItem(row, 1, QTableWidgetItem(str(scores.get('메시지 전달력', 0))))
            self.detail_table.setItem(row, 2, QTableWidgetItem(str(scores.get('창의성 및 독창성', 0))))
            self.detail_table.setItem(row, 3, QTableWidgetItem(str(scores.get('브랜드/제품 적합성', 0))))

            # 총점 (색상 적용)
            total_item = QTableWidgetItem(str(result['total_score']))
            if result['total_score'] >= 4.0:
                total_item.setBackground(Qt.green)
            elif result['total_score'] >= 3.0:
                total_item.setBackground(Qt.yellow)
            else:
                total_item.setBackground(Qt.red)
            self.detail_table.setItem(row, 4, total_item)

            # 추출된 설명
            predicted_desc = result.get('predicted_description', '추출 실패')
            predicted_item = QTableWidgetItem(
                predicted_desc[:50] + "..." if len(predicted_desc) > 50 else predicted_desc)
            predicted_item.setToolTip(predicted_desc)  # 전체 텍스트는 툴팁으로
            self.detail_table.setItem(row, 5, predicted_item)

            # 주요 이슈 (가장 낮은 점수의 이유)
            reasons = result['reasons']
            min_score_key = min(scores.keys(), key=lambda k: scores[k])
            main_issue = f"{min_score_key}: {reasons.get(min_score_key, '')}"
            main_issue_item = QTableWidgetItem(main_issue[:50] + "..." if len(main_issue) > 50 else main_issue)
            main_issue_item.setToolTip(main_issue)  # 전체 텍스트는 툴팁으로
            self.detail_table.setItem(row, 6, main_issue_item)

            # 재생성 버튼
            if result['total_score'] < 4.0:  # 4점 미만인 경우만 재생성 버튼 활성화
                regen_button = QPushButton('재생성')
                regen_button.setStyleSheet(self.get_button_style('#dc3545'))
                regen_button.clicked.connect(
                    lambda checked, sn=result['scene_number'], prompt=result['regeneration_prompt']:
                    self.regenerate_scene(sn, prompt)
                )
                self.detail_table.setCellWidget(row, 7, regen_button)

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

                # 추출된 설명 표시
                desc_label = QLabel(f"추출된 설명: {result.get('predicted_description', '없음')}")
                desc_label.setStyleSheet("font-style: italic; color: #666; margin: 5px 0;")
                desc_label.setWordWrap(True)
                scene_layout.addWidget(desc_label)

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

    def evaluate_storyboard(self, scenes_data):
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
