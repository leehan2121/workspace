# generator.py
import json
import re
from pathlib import Path
from datetime import datetime

from prompts import build_prompt_json
from llm_client import ollama_generate

DEBUG_DIR = Path("debug")
RAW_DIR = DEBUG_DIR / "llm_raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

def _ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _save_raw(topic_tag: str, stage: str, text: str):
    safe = re.sub(r"[^a-zA-Z0-9_\-()가-힣]", "_", topic_tag)[:80]
    p = RAW_DIR / f"{_ts()}__{safe}__{stage}.txt"
    with open(p, "w", encoding="utf-8") as f:
        f.write(text or "")

def _extract_json(text: str) -> dict:
    if not text:
        raise ValueError("LLM 응답이 비어있음")

    t = text.strip()

    # 혹시 ```json``` 으로 감쌌을 때
    m = re.search(r"```json\s*(\{.*?\})\s*```", t, flags=re.DOTALL | re.IGNORECASE)
    if m:
        return json.loads(m.group(1))

    # 그냥 {...}만 있을 때
    start = t.find("{")
    end = t.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(t[start:end + 1].strip())

    raise ValueError("LLM 응답에서 JSON을 추출하지 못함")

def _repair_yaml_like(raw: str) -> dict:
    """
    LLM이 아래처럼 YAML 비슷하게 뱉는 케이스 수리:
    {
      "title": "...",
      "body": |
        ...
    }
    """
    t = (raw or "").strip()

    title_m = re.search(r'"title"\s*:\s*"([^"]+)"', t)
    title = title_m.group(1).strip() if title_m else ""

    # body: | 시작점 찾기
    body_m = re.search(r'"body"\s*:\s*\|\s*\n', t)
    if not body_m:
        raise ValueError("YAML-like body( | ) 패턴 아님")

    body_start = body_m.end()
    body_block = t[body_start:]

    # 마지막 닫는 중괄호 잘라내기
    last_brace = body_block.rfind("}")
    if last_brace != -1:
        body_block = body_block[:last_brace].rstrip()

    # 들여쓰기 제거
    lines = body_block.splitlines()
    # 공통 indent 추정 (최소 2칸 이상일 때)
    indents = []
    for ln in lines:
        if ln.strip():
            indents.append(len(ln) - len(ln.lstrip(" ")))
    cut = min(indents) if indents else 0
    if cut >= 2:
        lines = [ln[cut:] if len(ln) >= cut else ln for ln in lines]

    body = "\n".join(lines).strip()
    return {"title": title, "body": body}

def _sanitize_body(text: str) -> str:
    """
    - 한자/일본어 제거
    - 긴 영어 문장 라인 제거
    - 프롬프트 잔재(역할/목표/출력 형식/입력 블록) 등장 시 그 지점부터 제거
    """
    if not text:
        return text

    # 프롬프트 잔재 컷(이 패턴이 본문에 나오면 그 아래는 버림)
    cut_markers = ["역할:", "목표:", "출력 공통 규칙:", "[입력]", "[출력 형식]"]
    for mk in cut_markers:
        idx = text.find(mk)
        if idx != -1:
            text = text[:idx].rstrip()

    out_lines = []
    for ln in text.splitlines():
        s = ln.strip()
        if not s:
            out_lines.append("")
            continue

        # 한자/일본어(히라가나/가타카나) 제거
        s = re.sub(r"[\u4E00-\u9FFF\u3040-\u30FF]+", "", s)

        # 영어가 너무 많은 라인은 제거(질문/설명 섞이는 것 방지)
        ascii_letters = sum(c.isascii() and c.isalpha() for c in s)
        korean_letters = sum("\uac00" <= c <= "\ud7a3" for c in s)
        if ascii_letters >= 25 and korean_letters < 5:
            continue

        # 이상한 “외계어” 같은 특수문자 폭주 라인 제거(너무 길면 컷)
        if len(s) > 300:
            s = s[:300] + "…"

        out_lines.append(s)

    cleaned = "\n".join(out_lines).strip()
    return cleaned

def generate_post_with_ollama(category, article, ollama_url, model, timeout=600, topic_tag=""):
    article_title = (article.get("title") or "").strip()
    topic_tag = topic_tag or category or "topic"

    prompt = build_prompt_json(category, article)
    _save_raw(topic_tag, "prompt", prompt)

    raw = ollama_generate(
        ollama_url=ollama_url,
        model=model,
        prompt=prompt,
        timeout=timeout
    )
    _save_raw(topic_tag, "response", raw)

    # 1) JSON 파싱 우선
    obj = None
    try:
        obj = _extract_json(raw)
    except Exception as e_json:
        _save_raw(topic_tag, "parse_json_error", repr(e_json))
        # 2) YAML-like 수리 시도
        try:
            obj = _repair_yaml_like(raw)
            _save_raw(topic_tag, "repair_used", "yaml_like_repair")
        except Exception as e_rep:
            _save_raw(topic_tag, "repair_error", repr(e_rep))
            # 3) 최후 fallback: 제목은 기사 제목, 본문은 raw
            obj = {"title": article_title or "(제목 없음)", "body": raw}

    title = (obj.get("title") or "").strip()
    body = (obj.get("body") or "").strip()

    if not title or title == "{" or title.startswith("{"):
        title = article_title or "(제목 없음)"

    body = _sanitize_body(body)

    # body 너무 짧으면 raw를 한번 더 정리해서 채움
    if len(body) < 200:
        body = _sanitize_body(raw)

    return title, body
