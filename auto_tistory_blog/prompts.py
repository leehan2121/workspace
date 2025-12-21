def build_prompt_json(category: str, article: dict) -> str:
    """
    LLM이 JSON으로만 응답하도록 강제하는 프롬프트.
    """
    base = build_prompt(category, article)
    return base + """

[출력 형식]
- 반드시 JSON만 출력하라. (설명/문장/코드블록/마크다운펜스 금지)
- YAML 문법(예: body: |) 절대 사용 금지.
- JSON 키는 정확히 다음과 같아야 한다:
  {
    "title": "블로그 제목",
    "body": "블로그 본문(\\n 포함한 '하나의 JSON 문자열')"
  }
- title은 60자 내외.
- body는 700~1800자 범위.
- 본문은 기본적으로 한국어로 작성하라. (필요 최소한의 영어 약어(AI, CEO 등)만 허용)
"""

def build_image_prompt_kor(title: str, topic: str) -> str:
    return f"""뉴스 썸네일용 일러스트.
주제: {topic}
제목: {title}
스타일: 깔끔한 플랫 일러스트, 상징적 오브젝트 중심, 텍스트 없음, 로고/실존인물 없음, 저작권 문제 없는 생성 이미지.
구도: 중앙 오브젝트 + 부드러운 배경, 고해상도."""