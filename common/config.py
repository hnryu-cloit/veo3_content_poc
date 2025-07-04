import argparse


parser = argparse.ArgumentParser(description="브랜드 영상 콘텐츠 스토리보드 생성")

#system prompt
parser.add_argument('--duration', type=int, default=15, help='영상 길이(초)')
parser.add_argument('--sections', type=int, default=3, help='섹션 수')
parser.add_argument('--output', default='storyboard.json', help='출력 파일')

# 옵션 플래그
parser.add_argument('--visual', type=bool, default=False, help='비주얼 요소 포함')
parser.add_argument('--audio', action='store_true', help='오디오 요소 포함')
parser.add_argument('--detailed', action='store_true', help='상세 설명 포함')