class AppPrompt:
    def __init__(self):
        print("AppPrompt")

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



class StoryPrompt:
    def __init__(self):
        print("StoryPrompt")

    def description_prompt(self):
        """각 scene 별 description 생성"""
        return """
            입력받은 scene 이미지는 광고 영상 중 일부 장면에 대한 이미지입니다.
            이미지를 보고 해당 scene에 해당하는 설명을 한 문장으로 작성해주세요.
            부분적인 묘사보다는 핵심 스토리에 대해 작성해주세요.
        """

    def score_prompt(self, scene_description, validation_description):
        """동일 scene간 description 비교"""
        return f"""
        
             아래의 동일 광고 scene에 대한 description에 대해 비교하려고 합니다.
             - 원본 설명: {scene_description}
             - 검증용 설명: {validation_description}\n\n
             
             **평가 지침**
             다음 세 가지 기준에 따라 각각 0~5점(0: 전혀 유사하지 않음, 5: 매우 유사함)으로 평가하세요.
             1. 메시지 전달력: 광고의 핵심 메시지가 스케치에서 명확하게 시각적으로 표현되어 있는가?
             2. 창의성 및 독창성: 스케치가 기존 광고와 차별화되는 창의적 아이디어와 표현 방식을 보여주는가?
             3. 브랜드/제품 적합성: 스케치가 브랜드의 정체성, 제품 특성, 타깃 소비자와 잘 부합하는가?
             세 기준의 점수를 기반으로 전체 비교 총점을 산출하고 각 항목별로  간단한 평가 이유와 개선점을 작성하세요.\n\n
             
             **출력 형식**
             아래의 JSON 형식으로 출력해주세요.
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
                    "총점": 0~15
                }}
        """

    def for_improve_prompt(self, generate_image_prompt):
        """개선된 프롬프트 생성을 위한 프롬프트"""
        return f"""
            기존 프롬프트: {generate_image_prompt}
            아래는 위 프롬프트로 생성된 장면에 대한 평가 결과입니다. 제공해주신 평가 기준(메시지 전달력, 창의성 및 독창성, 브랜드/제품 적합성)을 바탕으로 프롬프트를 개선합니다.
            - '점수'가 3점 이상인 경우는 '평가 이유'를 유지하는 방향으로 수정해주세요.
            - '점수'가 2점 이하인 경우는 '평가 이유'와 '개선점'을 반영하여 수정해주세요. 
            위의 요구사항을 반영하여 더 나은 scene 이미지 생성을 위한 프롬프트를 텍스트로 출력해주세요.
          """


    def image_prompt(self, data):
        """이미지 생성을 위한 프롬프트"""
        return f"""
            {data['visual']}{data['description']}
            위 장면에 대한 광고 스케치 이미지를 생성해주세요.
        """


class ValidPrompt:
    def __init__(self):
        print("ValidPrompt")

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