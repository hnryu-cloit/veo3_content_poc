
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


class ValidatorPrompt:


    def score_prompt(self):
        return """
        
        
        
        
        """
