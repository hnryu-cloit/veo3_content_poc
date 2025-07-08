import os
import shutil
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from PIL import Image
from common.gemini import Gemini

from google.genai.types import Part

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
        prompt_parts = []

        if scene.get('plot'):
            prompt_parts.append(f"전체 줄거리: {scene['plot']}")
        if scene.get('visual'):
            prompt_parts.append(f"시각적 묘사: {scene['visual']}")
        if scene.get('description'):
            prompt_parts.append(f"장면 묘사: {scene['description']}")
        if scene.get('mood'):
            prompt_parts.append(f"분위기: {scene['mood']}")
        if scene.get('audio'):
            prompt_parts.append(f"음향 효과: {scene['audio']}")
        if scene.get('text'):
            prompt_parts.append(f"자막/나레이션: {scene['text']}")

        base_prompt = "아래의 정보를 참고 하여 스토리보드 스케치 이미지를 만들어줘. "
        full_prompt = base_prompt + " | ".join(prompt_parts)

        return full_prompt


class ImageRegenerationThread(QThread):
    """이미지 재생성 스레드"""
    regeneration_completed = pyqtSignal(int, object, str)

    def __init__(self, scene_data, scene_number):
        super().__init__()
        self.scene_data = scene_data
        self.scene_number = scene_number
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

            # 새 이미지 생성
            new_image_path = self.regenerate_scene_image()
            self.regeneration_completed.emit(self.scene_number, new_image_path, "")

        except Exception as e:
            self.regeneration_completed.emit(self.scene_number, None, str(e))
        finally:
            import gc
            gc.collect()

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

    def create_regeneration_prompt(self):
        """재생성을 위한 프롬프트 생성 (기존보다 더 자세한 설명 추가)"""
        prompt_parts = []

        # 기본 스토리보드 지시문
        base_instruction = "아래의 정보를 참고하여 상세하고 개선된 스토리보드 스케치 이미지를 다시 생성해줘. 이전보다 더 생동감 있고 표현력이 풍부하게:"

        if self.scene_data.get('visual'):
            prompt_parts.append(f"시각적 묘사: {self.scene_data['visual']}")
        if self.scene_data.get('description'):
            prompt_parts.append(f"장면 묘사: {self.scene_data['description']}")
        if self.scene_data.get('mood'):
            prompt_parts.append(f"분위기: {self.scene_data['mood']}")
        if self.scene_data.get('audio'):
            prompt_parts.append(f"음향 효과: {self.scene_data['audio']}")
        if self.scene_data.get('text'):
            prompt_parts.append(f"자막/나레이션: {self.scene_data['text']}")

        # 추가 개선 지시문
        enhancement_instruction = "더욱 선명하고 감정적으로 표현력이 뛰어난 이미지로 만들어줘."

        full_prompt = f"{base_instruction} {' | '.join(prompt_parts)} {enhancement_instruction}"

        return full_prompt

    @staticmethod
    def regenerate_image(scene_data, scene_number, parent=None):
        """이미지 재생성 시작 (정적 메서드)"""
        # 재생성 확인 메시지
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            parent,
            '이미지 재생성',
            f'씬 #{scene_number}의 이미지를 다시 생성하시겠습니까?\n기존 이미지는 덮어씌워집니다.',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 재생성 스레드 시작
            regen_thread = ImageRegenerationThread(scene_data, scene_number)
            return regen_thread

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
                os.remove(temp_file_path)
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


class ValidationTextGenerator():
    """각 씬에 대한 이미지로부터 검증용 줄거리 생성"""
    def __init__(self, scenes):
        super().__init__()
        self.prompt = None
        self.scenes = scenes
        self.gemini = Gemini()
        self.temp_folder = './temp_save' # temp


    def run(self):
        image_files = []

        for f_name in os.listdir(self.temp_folder):
            if f_name.startswith('scene_'):
                try:
                    # 파일명에서 숫자 부분 추출 (예: _1.png -> 1)
                    suffix_part = f_name.split('_')[-1].split('.')[0]
                    image_number = int(suffix_part)
                    image_files.append((image_number, os.path.join(self.temp_folder, f_name)))
                except ValueError:
                    continue  # 숫자가 아닌 경우 건너뛰기

        # 파일명 접미사 번호순으로 정렬
        image_files.sort(key=lambda x: x[0])
        if len(image_files) != 8:
            print(f"경고: '{self.temp_folder}' 폴더에 8개의 이미지가 발견되지 않았습니다. 현재 {len(image_files)}개.")
            if len(image_files) == 0:
                print("이미지 파일을 찾을 수 없습니다. 파일명과 경로를 확인해주세요.")


        # 로컬에 저장된 이미지 bytes 형식으로 변환하기
        contents = []
        for image_file in image_files:
            with open(image_file[-1], 'rb') as f:
                img_bytes  = f.read()
                contents.append(Part.from_bytes(data=img_bytes, mime_type="image/png"))

        prompt = "이 8개의 씬 이미지는 하나의 이야기를 구성합니다. 각 이미지의 순서에 따라 전체적인 줄거리를 2~3줄 분량으로 작성해 주세요."

        contents.insert(0,prompt)

        try:
            response = self.gemini._call_gemini_multimodal(contents)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini API call failed: {e}")



if __name__ == "__main__":

    print("이미지 업로드 및 재생성 모듈이 로드되었습니다.")

    # 테스트 시나리오
    test_scene = {
        'scene_number': 1,
        'visual': '테스트 장면',
        'description': '테스트 설명',
        'mood': '테스트 분위기'
    }

    print(f"테스트 씬 데이터: {test_scene}")