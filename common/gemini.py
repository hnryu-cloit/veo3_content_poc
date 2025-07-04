import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
from dotenv import load_dotenv
from google import genai
from google.genai import types
from PIL import Image
from io import BytesIO
import base64

from common.logger import timefn
from common.logger import init_logger

logger = init_logger()


class Gemini:
    def __init__(self):
        load_dotenv()
        self.client = genai.Client(api_key=os.getenv('API_KEY'))
        self.model = 'gemini-2.0-flash'  #'gemini-2.5-flash-preview-05-20' | 'gemini-2.5-pro-preview-06-05'
        self.max_retries = 10
        self.initial_delay = 1

    def retry_with_delay(func):
        def wrapper(self, *args, **kwargs):
            delay = self.initial_delay
            for attempt in range(self.max_retries):
                try:
                    return func(self, *args, **kwargs)
                except Exception as e:
                    if attempt == self.max_retries - 1:
                        raise e
                    logger.error(f"gemini 호출 {attempt + 1}번째 실패: {e}")
                    time.sleep(delay)
                    delay *= 2

        return wrapper

    @retry_with_delay
    @timefn
    def _call_gemini_image_text(self, prompt, image, text, model=None):
        target_image = self.client.files.upload(file=image)
        response = self.client.models.generate_content(
            model=model if model else self.model,
            contents=[
                prompt,
                target_image,
                text,
            ],
            config={
                "response_mime_type": "application/json",
                # "response_schema": model_schema(),
            }
        )
        return response.text

    @retry_with_delay
    @timefn
    def _call_gemini_text(self, prompt, model=None):
        response = self.client.models.generate_content(
            model=model if model else self.model,
            contents=[
                prompt,
            ],
            config={
                "response_mime_type": "application/json",
            }
        )
        return response.candidates[0].content.parts[0].text

    @retry_with_delay
    @timefn
    def _call_gemini_text_stream(self, prompt, model=None):

        response = self.client.models.generate_content_stream(
            model=model if model else self.model,
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part(text=prompt)
                    ]
                ),
            ],
            config=types.GenerateContentConfig(
                temperature=1,
                top_p=1,
                max_output_tokens=8192,
                safety_settings=[types.SafetySetting(
                  category="HARM_CATEGORY_HATE_SPEECH",
                  threshold="OFF"
                ),types.SafetySetting(
                  category="HARM_CATEGORY_DANGEROUS_CONTENT",
                  threshold="OFF"
                ),types.SafetySetting(
                  category="HARM_CATEGORY_SEXUALLY_EXPLICIT",
                  threshold="OFF"
                ),types.SafetySetting(
                  category="HARM_CATEGORY_HARASSMENT",
                  threshold="OFF"
                )],
              )
        )
        return response

    @timefn
    def _call_imagen_text(self, prompt):
        response = self.client.models.generate_images(
            model='imagen-4.0-generate-preview-06-06',
            prompt=prompt,
            config=types.GenerateImagesConfig(
                number_of_images=1,
            )
        )
        image = Image.open(BytesIO(response.generated_images[0].image.image_bytes))
        return image