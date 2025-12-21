# prompts.py
# 카테고리별 프롬프트 템플릿 모음 (편집/해설형, 출처 명시 전제)

BASE_PROMPT = """역할:
너는 뉴스 편집자다. 아래 입력으로 주어진 뉴스 자료를 기반으로,
블로그에 올릴 ‘편집/해설’ 글을 작성한다.

목표:
- 단순 복사/요약이 아닌 재구성
- 사실 왜곡, 법적 리스크 최소화
- 독자가 맥락을 이해할 수 있게 설명

출력 공통 규칙:
1) 원문 문장 그대로 복사 금지(직접 인용은 1~2문장, 따옴표 사용).
2) 사실과 의견을 구분:
   - 사실: “보도에 따르면 / 기사에 따르면”
   - 의견: “해석해보면 / 개인적으로”
3) 확인되지 않은 추측, 단정 표현 금지.
4) 글 끝에 반드시 출처 명시(매체명 + 링크).

공통 글 구조:
- 제목
- 3줄 요약
- 본문(맥락 설명 + 쟁점 정리 + 독자가 궁금해할 포인트 Q&A 2~3개)
- 정리(한 문단)
- 출처(매체명 + 링크)

이제 아래 입력을 보고 글을 작성하라.
"""

POLITICS_ADDON = """[정치 뉴스 추가 규칙]
- 특정 정당/인물에 대한 평가적 단정 금지.
- 찬반이 갈리는 사안은 “엇갈린 반응”, “논란이 이어지고 있다” 식으로 서술.
- 추측성 내부 사정, 의도 분석은 피할 것.
- 감정적 표현 최소화, 설명형 문장 위주.

톤: 중립적, 해설형.
"""

GOSSIP_ADDON = """[연애·가십 뉴스 추가 규칙]
- 사생활 단정 금지.
- ‘열애 확정’, ‘결별 확정’ 같은 표현은 기사에 명시되지 않으면 사용 금지.
- 루머/추측은 “보도에서는 ~라고 전해졌다” 수준으로만 언급.
- 인물 비난, 조롱, 선정적 표현 금지.

톤: 가볍지만 선 넘지 않게.
"""

SOCIAL_ADDON = """[사회·사건 뉴스 추가 규칙]
- 가해/피해를 단정하지 말 것(수사/조사 중이면 그 상태를 명시).
- 자극적인 표현, 공포 조장 표현 피하기.
- 숫자·날짜·지명은 입력값 그대로 사용.

톤: 차분하고 설명 위주.
"""

KPOP_ADDON = """[K-POP/문화 뉴스 추가 규칙]
- 과장/단정 표현 금지(‘역대급’, ‘확정’ 등).
- 성과/순위/기록은 입력에 있는 사실만 사용.
- 팬덤 갈등 조장 표현 피하기.

톤: 밝고 정보 중심.
"""

CATEGORY_ADDONS = {
    "politics": POLITICS_ADDON,
    "gossip": GOSSIP_ADDON,
    "social": SOCIAL_ADDON,
    "kpop": KPOP_ADDON,
}

def build_prompt(category: str, article: dict) -> str:
    addon = CATEGORY_ADDONS.get(category, "")
    title = (article.get("title") or "").strip()
    lead = (article.get("lead") or "").strip()
    excerpt = (article.get("excerpt") or "").strip()
    link = (article.get("link") or "").strip()
    source = (article.get("source") or "").strip()

    lines = []
    lines.append(BASE_PROMPT)
    if addon:
        lines.append(addon)

    lines.append("[입력]")
    lines.append(f"- 기사 제목: {title}")
    if lead:
        lines.append(f"- 기사 요약/리드: {lead}")
    if excerpt:
        lines.append(f"- 기사 본문 일부(짧게): {excerpt}")
    lines.append(f"- 원문 링크(URL): {link}")
    if source:
        lines.append(f"- 매체/출처: {source}")
    lines.append(f"- 카테고리: {category}")

    return "\n".join(lines)

def build_prompt_json(category: str, article: dict) -> str:
    """
    LLM이 JSON으로만 응답하도록 강제하는 프롬프트.
    """
    base = build_prompt(category, article)
    return base + """

[출력 형식]
- 반드시 JSON만 출력하라. (설명/문장/코드블록 금지)
- JSON 키는 정확히 다음과 같아야 한다:
  {
    "title": "블로그 제목",
    "body": "블로그 본문(마크다운 가능)"
  }
- title은 60자 내외, body는 700~1800자 범위로 작성.
"""
