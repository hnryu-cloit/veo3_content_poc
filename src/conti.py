import os
import shutil
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PIL import Image
from common.gemini import Gemini
from common.prompt import StoryPrompt

storyPrompt = StoryPrompt()


class ImageGenerationThread(QThread):
    scene_completed = pyqtSignal(int, object, str)
    generation_completed = pyqtSignal()

    def __init__(self, scenes):
        super().__init__()
        self.scenes = scenes
        self.gemini = Gemini()
        self.temp_folder = './temp'

        os.makedirs(self.temp_folder, exist_ok=True)

    def run(self):
        """각 씬에 대해 이미지 생성"""
        for i, scene in enumerate(self.scenes):
            try:
                image_path = self.generate_scene_image(scene, i + 1)
                self.scene_completed.emit(i + 1, image_path, "")
            except Exception as e:
                self.scene_completed.emit(i + 1, None, str(e))
            finally:
                import gc
                gc.collect()
        self.generation_completed.emit()

    def generate_scene_image(self, scene, scene_number):
        """실제 이미지 생성 함수 (Imagen4 API 사용)"""
        prompt = self.create_scene_image_prompt(scene)
        temp_path = os.path.join(self.temp_folder, f"scene_{scene_number}.png")

        try:
            if self.gemini:
                sketch_image = self.gemini._call_imagen_text(prompt)
                sketch_image.save(temp_path, 'PNG')
            else:
                dummy_image = Image.new('RGB', (512, 512), color='lightgray')
                dummy_image.save(temp_path, 'PNG')

            return temp_path
        except Exception as e:
            raise Exception(f"이미지 생성 실패: {str(e)}")
        finally:
            import gc
            gc.collect()

    def create_scene_image_prompt(self, scene):
        """씬 정보를 바탕으로 이미지 생성 프롬프트 생성"""
        return storyPrompt.image_prompt(scene)


class ImageRegenerationThread(QThread):
    """이미지 재생성 스레드"""
    regeneration_completed = pyqtSignal(int, object, str)

    def __init__(self, scene_data, scene_number, improved_prompt=None):
        super().__init__()
        self.scene_data = scene_data
        self.scene_number = scene_number
        self.improved_prompt = improved_prompt
        self.temp_folder = './temp'

        # Gemini 초기화
        try:
            from common.gemini import Gemini
            self.gemini = Gemini()
        except ImportError:
            self.gemini = None
            print("Gemini module not found - using dummy images")

        os.makedirs(self.temp_folder, exist_ok=True)

    def run(self):
        """이미지 재생성 실행"""
        try:
            # 기존 이미지 파일 삭제 (있다면)
            existing_file = os.path.join(self.temp_folder, f"scene_{self.scene_number}.png")
            if os.path.exists(existing_file):
                os.remove(existing_file)

            # 개선된 프롬프트가 있는 경우 사용
            if self.improved_prompt and 'improved_description' in self.scene_data:
                new_image_path = self.regenerate_with_improved_prompt()
            else:
                new_image_path = self.regenerate_scene_image()

            self.regeneration_completed.emit(self.scene_number, new_image_path, "")

        except Exception as e:
            self.regeneration_completed.emit(self.scene_number, None, str(e))
        finally:
            import gc
            gc.collect()

    def regenerate_with_improved_prompt(self):
        """개선된 프롬프트로 이미지 재생성"""
        # 개선된 설명을 사용한 프롬프트 생성
        improved_description = self.scene_data.get('improved_description', '')

        # 기본 씬 정보와 개선된 설명을 결합
        enhanced_scene_data = self.scene_data.copy()
        enhanced_scene_data['description'] = improved_description

        prompt = self.create_enhanced_prompt(enhanced_scene_data)
        temp_path = os.path.join(self.temp_folder, f"scene_{self.scene_number}.png")

        try:
            if self.gemini:
                sketch_image = self.gemini._call_imagen_text(prompt)
                sketch_image.save(temp_path, 'PNG')
            else:
                # 더미 이미지 생성 (테스트용) - 개선된 버전임을 나타내는 색상
                import random
                improved_colors = ['lightsteelblue', 'lightseagreen', 'lightsalmon', 'lightgoldenrodyellow',
                                   'lightpink']
                dummy_image = Image.new('RGB', (512, 512), color=random.choice(improved_colors))
                dummy_image.save(temp_path, 'PNG')

            return temp_path

        except Exception as e:
            raise Exception(f"이미지 재생성 실패: {str(e)}")

    def regenerate_scene_image(self):
        """씬 이미지 재생성"""
        prompt = self.create_regeneration_prompt()
        temp_path = os.path.join(self.temp_folder, f"scene_{self.scene_number}.png")

        try:
            if self.gemini:
                # 실제 Imagen4 API 호출
                sketch_image = self.gemini._call_imagen_text(prompt)
                sketch_image.save(temp_path, 'PNG')
            else:
                # 더미 이미지 생성 (테스트용) - 색상을 다르게 해서 재생성 표시
                import random
                colors = ['lightblue', 'lightgreen', 'lightcoral', 'lightyellow', 'lightpink']
                dummy_image = Image.new('RGB', (512, 512), color=random.choice(colors))
                dummy_image.save(temp_path, 'PNG')

            return temp_path

        except Exception as e:
            raise Exception(f"이미지 재생성 실패: {str(e)}")

    def create_enhanced_prompt(self, enhanced_scene_data):
        """개선된 씬 데이터로 프롬프트 생성"""
        try:
            # StoryPrompt를 사용하여 기본 프롬프트 생성
            base_prompt = storyPrompt.image_prompt(enhanced_scene_data)

            # 개선 지시사항 추가
            enhancement_instructions = """

            추가 개선 지시사항:
            - 더욱 선명하고 고품질의 이미지로 생성
            - 광고의 핵심 메시지가 명확히 드러나도록 구성
            - 브랜드 정체성과 제품 특성을 잘 반영
            - 창의적이고 독창적인 시각적 표현 사용
            - 전문적이고 임팩트 있는 광고 이미지 스타일
            """

            return base_prompt + enhancement_instructions

        except Exception as e:
            # StoryPrompt 사용에 실패한 경우 기본 프롬프트 생성
            return self.create_fallback_prompt(enhanced_scene_data)

    def create_regeneration_prompt(self):
        """기본 재생성 프롬프트 생성"""
        try:
            # StoryPrompt를 사용하여 기본 프롬프트 생성
            base_prompt = storyPrompt.image_prompt(self.scene_data)

            # 재생성 지시사항 추가
            regeneration_instructions = """

            재생성 지시사항:
            - 이전 버전보다 더 나은 품질로 생성
            - 광고 목적에 더 적합하도록 개선
            - 시각적 임팩트 강화
            """

            return base_prompt + regeneration_instructions

        except Exception as e:
            # StoryPrompt 사용에 실패한 경우 기본 프롬프트 생성
            return self.create_fallback_prompt(self.scene_data)

    def create_fallback_prompt(self, scene_data):
        """StoryPrompt 사용 실패 시 대체 프롬프트 생성"""
        description = scene_data.get('description', '')
        visual = scene_data.get('visual', '')
        mood = scene_data.get('mood', '')

        prompt = f"""
        광고 스토리보드용 고품질 이미지를 생성해주세요.

        장면 설명: {description}
        시각적 요소: {visual}
        분위기: {mood}

        스타일: 전문적인 광고 이미지, 고화질, 선명함
        """

        return prompt

    @staticmethod
    def regenerate_image(scene_data, scene_number, parent=None, improved_prompt=None):
        """이미지 재생성 시작"""
        # 재생성 확인 메시지
        from PyQt5.QtWidgets import QMessageBox

        message = f'Scene #{scene_number}의 이미지를 다시 생성하시겠습니까?\n기존 이미지는 덮어씌워집니다.'
        if improved_prompt:
            message += '\n\n개선된 프롬프트가 적용됩니다.'

        reply = QMessageBox.question(
            parent,
            '이미지 재생성',
            message,
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 재생성 스레드 시작
            regen_thread = ImageRegenerationThread(scene_data, scene_number, improved_prompt)
            return regen_thread

        return None

    @staticmethod
    def regenerate_with_improved_prompt(scene_data, scene_number, improved_prompt, parent=None):
        """개선된 프롬프트로 이미지 재생성"""
        try:
            # 씬 데이터에 개선된 설명 추가
            enhanced_scene_data = scene_data.copy()
            enhanced_scene_data['improved_description'] = improved_prompt

            # 재생성 스레드 생성
            regen_thread = ImageRegenerationThread(enhanced_scene_data, scene_number, improved_prompt)
            return regen_thread

        except Exception as e:
            if parent:
                QMessageBox.critical(parent, '오류', f'재생성 준비 중 오류가 발생했습니다: {str(e)}')
            return None


class ImageUpload:

    @staticmethod
    def open_file_dialog(parent=None, scene_number=None):
        """파일 선택 다이얼로그 열기"""
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(
            parent,
            f" #{scene_number} 이미지 선택" if scene_number else "이미지 선택",
            "",
            "이미지 파일 (*.png *.jpg *.jpeg);;PNG 파일 (*.png);;JPEG 파일 (*.jpg *.jpeg)"
        )
        return file_path

    @staticmethod
    def validate_image_file(file_path):
        """이미지 파일 유효성 검사"""
        if not file_path or not os.path.exists(file_path):
            return False, "파일이 존재하지 않습니다."

        valid_extensions = ['.png', '.jpg', '.jpeg']
        file_ext = os.path.splitext(file_path)[1].lower()
        if file_ext not in valid_extensions:
            return False, "지원하지 않는 파일 형식입니다. (png, jpg, jpeg만 지원)"

        # 파일 크기 검사 (10MB 제한)
        file_size = os.path.getsize(file_path)
        if file_size > 10 * 1024 * 1024:  # 10MB
            return False, "파일 크기가 너무 큽니다. (최대 10MB)"

        # 이미지 파일 유효성 검사
        try:
            with Image.open(file_path) as img:
                img.verify()
            return True, "유효한 이미지 파일입니다."
        except Exception as e:
            return False, f"유효하지 않은 이미지 파일입니다: {str(e)}"

    @staticmethod
    def copy_to_temp(file_path, scene_number, temp_folder='./temp'):
        """선택된 이미지를 임시 폴더로 복사"""
        try:
            # 임시 폴더 생성
            os.makedirs(temp_folder, exist_ok=True)

            # 파일 확장자 가져오기
            _, ext = os.path.splitext(file_path)

            # 대상 파일 경로 생성
            temp_file_path = os.path.join(temp_folder, f"scene_{scene_number}{ext}")

            # 파일 복사
            shutil.copy2(file_path, temp_file_path)

            if ext.lower() != '.png':
                png_path = os.path.join(temp_folder, f"scene_{scene_number}.png")
                with Image.open(temp_file_path) as img:
                    # RGBA 모드로 변환 (투명도 지원)
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    img.save(png_path, 'PNG')

                # 원본 파일 삭제
                # os.remove(temp_file_path)
                temp_file_path = png_path

            return temp_file_path, "이미지가 성공적으로 업로드되었습니다."

        except Exception as e:
            return None, f"이미지 복사 중 오류가 발생했습니다: {str(e)}"

    @staticmethod
    def upload_image(parent=None, scene_number=None, temp_folder='./temp'):
        """통합 이미지 업로드 함수"""
        # 1. 파일 선택
        file_path = ImageUpload.open_file_dialog(parent, scene_number)
        if not file_path:
            return None, "파일이 선택되지 않았습니다."

        # 2. 파일 유효성 검사
        is_valid, message = ImageUpload.validate_image_file(file_path)
        if not is_valid:
            return None, message

        # 3. 임시 폴더로 복사
        temp_path, copy_message = ImageUpload.copy_to_temp(file_path, scene_number, temp_folder)
        if not temp_path:
            return None, copy_message

        return temp_path, copy_message