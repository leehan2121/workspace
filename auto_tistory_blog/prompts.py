# prompts.py
import json

def build_prompt_json(category: str, article: dict) -> str:
    """
    Ollama에게 '결과물만' JSON으로 뽑게 만드는 프롬프트.
    - HTML 금지(<br> 금지)
    - 한국어 고정
    - 섹션/구조/길이 강제
    - 정치 카테고리는 중립 톤 강제
    """

    title = (article.get("title") or "").strip()
    source = (article.get("source") or "").strip()
    url = (article.get("link") or "").strip()
    pubdate = (article.get("date") or "").strip()

    # ===== 공통 규칙 =====
    base_rules = """
- Output MUST be valid JSON only.
- Do NOT include explanations, comments, markdown, or HTML.
- Do NOT use <br> or any HTML tags.
- Write in Korean.
- Distinguish facts and opinions clearly.
- Avoid unverified speculation or definitive claims.
""".strip()

    # ===== 문단 예시 =====
    paragraph_example = """
{
  "title": "제목",
  "summary": [
    "요약 문장 1",
    "요약 문장 2",
    "요약 문장 3"
  ],
  "body": [
    {
      "section": "배경",
      "content": "배경 설명 문단"
    },
    {
      "section": "핵심 내용",
      "content": "기사 핵심 재구성"
    },
    {
      "section": "해설",
      "content": "의미와 맥락 해설"
    }
  ],
  "source": {
    "name": "매체명",
    "url": "원문 링크"
  }
}
""".strip()

    # ===== 정치 카테고리 추가 규칙 =====
    politics_rules = ""
    if category == "politics":
        politics_rules = """
- Maintain a neutral and balanced tone.
- Do NOT support or oppose any political party or individual.
- Clearly separate reported facts from interpretation.
""".strip()

    # ⚠️ 핵심 수정 포인트
    extra_constraints = ""
    if politics_rules:
        extra_constraints = "Additional constraints for politics:\n" + politics_rules

    # ===== 최종 프롬프트 =====
    prompt = f"""
You are a news editor.

Rules:
{base_rules}

JSON format example:
{paragraph_example}

{extra_constraints}

News input:
- title: {title}
- source: {source}
- date: {pubdate}
- url: {url}

Now produce the JSON object.
""".strip()

    return prompt
