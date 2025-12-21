# generator.py
import json
import re
from pathlib import Path
from datetime import datetime
import requests

from prompts import build_prompt_json

DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)

def _now_tag():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def _clean_weird_lang(text: str) -> str:
    """
    - 한글/영문/숫자/일반 기호는 유지
    - 일본어(히라가나/가타카나) 제거
    - 베트남식 결합문자(라틴 확장) 일부 제거(너 로그의 kết 같은 것)
    - 과도한 공백 정리
    """
    if not text:
        return text

    # 일본어 제거
    text = re.sub(r"[\u3040-\u30FF]+", "", text)

    # 라틴 확장(대충) 제거: 필요 시 완화 가능
    text = re.sub(r"[\u0100-\u024F]+", "", text)

    # 제어문자 제거
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)

    # 공백 정리
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()

def _extract_first_json_object(text: str):
    """
    텍스트에서 가장 바깥 JSON 오브젝트를 찾아 파싱 시도.
    """
    if not text:
        return None

    # 코드펜스 제거
    text = re.sub(r"```(?:json)?", "", text).strip()

    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    candidate = text[start:end+1].strip()

    # YAML 스타일 '"body": |' 을 '"body":'로 1차 정리(그래도 JSON이 되진 않지만, 후속 처리용)
    candidate = candidate.replace('"body": |', '"body":')

    try:
        return json.loads(candidate)
    except Exception:
        return None

def _resolve_final_url(url: str) -> str:
    """
    구글뉴스 RSS 링크가 길고 파라미터가 많아서,
    가능하면 리다이렉트 최종 URL로 정리한다.
    실패하면 원본 URL 유지.
    """
    if not url:
        return url
    try:
        r = requests.get(url, allow_redirects=True, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        return r.url or url
    except Exception:
        return url

def generate_post_with_ollama(
    category: str,
    article: dict,
    ollama_url: str,
    model: str,
    timeout: int = 600,
    topic_tag: str = "topic"
):
    """
    ✅ 핵심 변경점:
    - Ollama /api/generate 에 format(JSON schema)를 넣어서 JSON 출력 강제
    - 파싱 실패 시 글 업로드를 막기 위한 디버깅 자료 저장
    """

    # 출처 URL 정리(가능한 경우만)
    if article.get("link"):
        article["link"] = _resolve_final_url(article["link"])

    prompt = build_prompt_json(category, article)

    # 디버그: 프롬프트 저장
    prompt_path = DEBUG_DIR / f"llm_prompt_{topic_tag}_{_now_tag()}.txt"
    _write_text(prompt_path, prompt)

    endpoint = ollama_url.rstrip("/") + "/api/generate"

    # Ollama format(JSON schema) 강제
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "body": {"type": "string"},
            "summary": {"type": "string"},
            "source": {"type": "string"},
            "url": {"type": "string"}
        },
        "required": ["title", "body"]
    }

    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "format": schema,
        "options": {
            # ✅ 속도/일관성 튜닝
            "temperature": getattr(__import__("config"), "LLM_TEMPERATURE", 0.4),
            "top_p": getattr(__import__("config"), "LLM_TOP_P", 0.9),
            "num_predict": getattr(__import__("config"), "LLM_NUM_PREDICT", 900),
        }
    }

    # 디버그: 요청 payload 저장(민감정보 없음)
    _write_text(DEBUG_DIR / f"llm_payload_{topic_tag}_{_now_tag()}.json", json.dumps(payload, ensure_ascii=False, indent=2))

    # 요청
    r = requests.post(endpoint, json=payload, timeout=(10, timeout))
    r.raise_for_status()
    data = r.json()

    raw = data.get("response", "")
    raw_path = DEBUG_DIR / f"llm_raw_{topic_tag}_{_now_tag()}.txt"
    _write_text(raw_path, raw)

    parsed = None

    # 1) format이 잘 먹으면 raw 자체가 JSON string이거나, 이미 깔끔한 JSON이 됨
    try:
        parsed = json.loads(raw)
    except Exception:
        # 2) 혹시 포맷이 어겨졌다면 텍스트에서 JSON만 추출
        parsed = _extract_first_json_object(raw)

    if not isinstance(parsed, dict):
        # 파싱 실패하면, 여기서 멈추는 게 맞다(그대로 올리면 프롬프트/JSON 유출)
        raise RuntimeError(f"E_LLM_PARSE_FAILED: response not JSON. saved={raw_path}")

    title = (parsed.get("title") or "").strip()
    body = (parsed.get("body") or "").strip()

    # YAML pipe 흔적 제거
    body = re.sub(r'^\|\s*\n', '', body).strip()

    # 언어 섞임/이상문자 완화
    title = _clean_weird_lang(title)
    body = _clean_weird_lang(body)

    # 출처 강제 부착(원문 링크는 짧아진 URL)
    src = article.get("source") or parsed.get("source") or "출처"
    url = article.get("link") or parsed.get("url") or ""
    if url:
        body = body.rstrip() + f"\n\n출처: {src} ({url})\n"

    # 비어있으면 방어
    if not title:
        title = article.get("title", "제목 없음").strip()
    if not body:
        raise RuntimeError("E_LLM_BODY_EMPTY")

    return title, body
