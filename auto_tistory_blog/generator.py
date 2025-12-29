# generator.py
import json
import re
from pathlib import Path
from datetime import datetime
import requests

from prompts import build_prompt_json

DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)

def extract_body(result: dict) -> str:
    """
    LLM 결과 dict에서 본문을 안전하게 추출한다.
    body 키가 없거나 다른 키로 올 경우를 대비한 fallback.

    NOTE(KO): 모델이 {body} 대신 {content/text/article} 로 주는 케이스가 있어
              본문이 비는 문제를 방지한다.
    NOTE(EN): Fallback extraction for varying JSON keys.
    """
    if not isinstance(result, dict):
        return ""
    for key in ("body", "content", "article", "text"):
        v = result.get(key)
        if isinstance(v, str) and v.strip():
            return v.strip()
    return ""



def _now_tag():
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text if text is not None else "")


def _clean_weird_lang(text: str) -> str:
    """
    - 일본어(히라가나/가타카나) 제거
    - 라틴 확장 일부 제거
    - 한자(중국어/한자) 제거
    - 제어문자 제거
    - 공백 정리
    """
    if not text:
        return text

    text = re.sub(r"[\u3040-\u30FF]+", "", text)          # Japanese
    text = re.sub(r"[\u0900-\u097F]+", "", text)          # Devanagari
    text = re.sub(r"[\u0400-\u04FF]+", "", text)          # Cyrillic
    text = re.sub(r"[\u0600-\u06FF]+", "", text)          # Arabic
    text = re.sub(r"[\u0100-\u024F]+", "", text)          # Latin ext (accented)
    text = re.sub(r"[\u4E00-\u9FFF]+", "", text)          # CJK ideographs (Hanja)
    text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)  # controls
    text = re.sub(r"[ \t]+\n", "\n", text)
    text = re.sub(r"\n{4,}", "\n\n\n", text)
    return text.strip()


def _strip_english_except_whitelist(text: str, whitelist=None) -> str:
    """
    본문에서 불필요한 영문 단어를 제거하되, 화이트리스트 토큰(AI/CEO 등)은 유지한다.
    Remove stray English words while keeping whitelisted tokens (e.g., AI, CEO).
    """
    if not text:
        return text
    whitelist = whitelist or ["AI", "CEO", "K-POP", "IT", "SD", "§§BODY_IMG§§", "§§CTX_IMG§§"]
    placeholders = {}
    out = text

    # 1) whitelist 토큰을 placeholder로 치환 / replace whitelist tokens with placeholders
    for i, token in enumerate(whitelist):
        ph = f"__WL_{i}__"
        placeholders[ph] = token
        out = out.replace(token, ph)

    # 2) 남은 영문 단어(연속된 알파벳)를 제거 / remove remaining English word sequences
    out = re.sub(r"[A-Za-z]{2,}", "", out)

    # 3) placeholder 복원 / restore placeholders
    for ph, token in placeholders.items():
        out = out.replace(ph, token)

    # 4) 공백 정리 / tidy spaces
    out = re.sub(r"[ ]{2,}", " ", out)
    out = re.sub(r"\s+\n", "\n", out)
    return out




def _normalize_paragraphs(paras):
    """문단 리스트를 정리한다 (빈값 제거, 공백 정리).
    Normalize paragraph list (drop empties, trim spaces)."""
    if not paras:
        return []
    out = []
    for p in paras:
        p = (p or "").strip()
        p = re.sub(r"\s+", " ", p)
        if p:
            out.append(p)
    return out


def _dedupe_paragraphs(paras):
    """중복/유사 문단을 간단히 제거한다.
    Remove exact/near-duplicate paragraphs (lightweight)."""
    seen = set()
    out = []
    for p in paras:
        key = re.sub(r"\s+", " ", p).strip()
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _dedupe_sentences_in_text(text: str) -> str:
    """같은 문장 반복을 줄인다(완전 동일 문장 기준).
    Reduce repeated sentences (exact match)."""
    if not text:
        return text
    # 문장 분리 (한국어 기준 간단 split) / naive sentence split for Korean
    parts = re.split(r"(?<=[\.\!\?。！？」])\s+|(?<=다\.)\s+|(?<=다\?)\s+|(?<=다\!)\s+", text.strip())
    out = []
    seen = set()
    for s in parts:
        s = s.strip()
        if not s:
            continue
        key = re.sub(r"\s+", " ", s)
        if key in seen:
            continue
        seen.add(key)
        out.append(s)
    return " ".join(out).strip()


def _assemble_body_from_parts(summary, context, analysis, conclusion) -> str:
    """JSON 파트를 받아 '하나의 글'로 합친다.
    Combine JSON parts into a single blog post body."""
    summary = _normalize_paragraphs(summary)
    context = _normalize_paragraphs(context)
    analysis = _normalize_paragraphs(analysis)
    conclusion = (conclusion or "").strip()

    # 상단 3줄 요약은 라벨 없이 bullet로 / bullets without labels
    bullets = []
    for s in summary[:3]:
        s = re.sub(r"^[-•\d\)\.\s]+", "", s).strip()
        if s:
            bullets.append(f"- {s}")

    paras = []
    paras.extend(context)
    paras.extend(analysis)
    if conclusion:
        paras.append(conclusion)

    paras = _dedupe_paragraphs(paras)
    paras = [ _dedupe_sentences_in_text(p) for p in paras ]

    body_parts = []
    if bullets:
        body_parts.append("\n".join(bullets))
    body_parts.extend(paras)

    # 문단은 두 줄바꿈으로 / separate paragraphs with blank line
    body = "\n\n".join([p for p in body_parts if p.strip()]).strip()
    return body


def _sentence_newlineize(text: str) -> str:
    """문장 끝마다 줄바꿈을 넣어 가독성을 높인다.
    Add newlines after sentence endings for readability.

    NOTE(KO): '한 문장 끝나면 내려쓰기' 요구 반영.
    NOTE(EN): This is a formatting-only transform; it does not invent content.
    """
    if not text:
        return text

    t = (text or "").strip()
    # 1) 한국어 종결 '다.' '다!' '다?' 뒤 공백/개행 -> 개행으로 통일
    t = re.sub(r"(?<=[\uAC00-\uD7A3]다[\.\!\?])\s+", "\n", t)
    # 2) 일반 문장부호(.!?) 뒤 공백 -> 개행 (약어/숫자 케이스는 완벽하지 않음)
    t = re.sub(r"(?<=[\.\!\?])\s+(?=[\uAC00-\uD7A3A-Za-z0-9\"\(\[])", "\n", t)
    # 3) 과도한 연속 개행 정리
    t = re.sub(r"\n{3,}", "\n\n", t)
    return t.strip()


def _format_two_section_body(summary: list, main_text: str, body_marker: str) -> str:
    """요약/본문을 '라벨 없이' 구성한다.

    요구사항:
    - 글 본문에 '요약', '본문' 같은 라벨 텍스트를 남기지 않는다.
    - 요약과 본문은 '빈 줄 5개'로만 구분한다.
    - body_marker(예: §§BODY_IMG§§)는 '본문 이미지 삽입 위치'로만 사용하며,
      티스토리 봇이 마커를 찾아 삭제한 뒤 이미지 삽입을 수행한다.
    - 내용이 빈약하면 '기사에서 확인되지 않는다' 같은 표현은 가능하지만,
      새로운 사실을 만들어내지는 않는다.
    """
    summary = _normalize_paragraphs(summary or [])

    # --- build summary lines ---
    lines = []
    for s in summary[:6]:
        s = re.sub(r"^[-•\d\)\.\s]+", "", (s or "")).strip()
        if s:
            lines.append(s)

    main_block = _sentence_newlineize(main_text or "").strip()

    # summary가 비어 있으면, 본문에서 '첫 3문장/라인'을 요약으로 추출(내용 생성 아님)
    if not lines and main_block:
        cand = [ln.strip() for ln in re.split(r"[\n]+", main_block) if ln.strip()]
        for ln in cand:
            if ln and ln not in lines:
                lines.append(ln)
            if len(lines) >= 3:
                break

    summary_block = "\n".join([_sentence_newlineize(x) for x in lines]).strip()

    out_parts = []
    if summary_block:
        out_parts.append(summary_block)

    # 요약-본문 구분: 빈 줄 5개
    out_parts.append("\n\n\n\n\n")

    # 본문 이미지 마커 위치
    out_parts.append(body_marker)

    if main_block:
        out_parts.append(main_block)
    else:
        out_parts.append("기사 원문에서 본문 내용을 충분히 확인하기 어렵다.")

    body = "\n".join([p for p in out_parts if p is not None]).strip()

    # 안전장치: 마커가 깨져 남는 경우 제거
    body = body.replace("§§_§§", "").strip()
    return body


def _build_retry_prompt_kor(base_prompt: str, fail_reason: str) -> str:
    """가드 실패 시, 초안(draft)을 주지 않고 '처음부터 재생성'시키는 리트라이 프롬프트.

    Retry prompt that forces regeneration from scratch (no draft leakage).
    - leakage (유출): 이전 출력에 섞인 한자/잡문자가 다음 출력으로 전염되는 문제
    """
    return (
        base_prompt
        + "\n\n[추가 지시: 1차 출력이 규칙 위반으로 실패했다]\n"
        + f"- 실패 사유: {fail_reason}\n"
        + "- 위 사유를 반드시 해결하라.\n"
        + "- 특히 title/body에 한글 외 문자가 1개라도 섞이면 실패다.\n"
        + "- 본문 길이가 부족하면 각 섹션에 구체 사실/수치/배경을 추가해 확장하라.\n"
        + "- 결과는 반드시 JSON 1개만 출력하라.\n"
    )


def _extract_first_json_object(text: str):
    if not text:
        return None

    cleaned = re.sub(r"```(?:json)?", "", text).strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    
    candidate = cleaned[start:end + 1].strip()
    # 제어문자 제거 (control chars)
    candidate = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", candidate).strip()
    candidate = candidate.replace('"body": |', '"body":')

    try:
        return json.loads(candidate)
    except Exception:
        return None


def _resolve_final_url(url: str) -> str:
    if not url:
        return url
    try:
        r = requests.get(url, allow_redirects=True, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
        return r.url or url
    except Exception:
        return url


def _html_escape(s: str) -> str:
    if s is None:
        return ""
    return (s.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;"))


def _make_fail_preview_html(topic_tag: str, title: str, body: str, reason: str) -> Path:
    p = DEBUG_DIR / f"fail_guard_{topic_tag}_{_now_tag()}.html"
    html = f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<title>FAIL GUARD PREVIEW</title>
<style>
  body{{font-family: Arial, sans-serif; margin:20px; line-height:1.5;}}
  .box{{padding:12px; border:1px solid #ddd; border-radius:10px; margin:12px 0;}}
  .reason{{background:#fff4f4; border-color:#ffcccc;}}
  pre{{white-space:pre-wrap; word-break:break-word;}}
</style>
</head>
<body>
<h2>LLM Guard 실패</h2>
<div class="box reason"><b>Reason:</b> {_html_escape(reason)}</div>

<div class="box">
  <h3>Title</h3>
  <pre>{_html_escape(title)}</pre>
</div>

<div class="box">
  <h3>Body</h3>
  <pre>{_html_escape(body)}</pre>
</div>
</body>
</html>"""
    _write_text(p, html)
    return p


def _contains_cjk_ideographs(text: str) -> bool:
    # 한자 영역(중국어/한자 포함 여부). 한국어-only 정책이면 걸러야 함
    return bool(re.search(r"[\u4E00-\u9FFF]", text or ""))


def _validate_post_quality(title: str, body: str, topic_tag: str):
    import config

    min_body_chars = getattr(config, "LLM_MIN_BODY_CHARS", 0)
    min_paragraphs = getattr(config, "LLM_MIN_PARAGRAPHS", 0)
    min_title_chars = getattr(config, "LLM_MIN_TITLE_CHARS", 8)
    max_title_chars = getattr(config, "LLM_MAX_TITLE_CHARS", 80)

    banned_patterns = getattr(config, "LLM_BANNED_PATTERNS", [
        r"```",
        r"(?i)\bassistant\s*:",
        r"(?i)\bsystem\s*:",
        r"(?i)\buser\s*:",
        r"(?i)\bas an ai\b",
        r"(?i)\bprompt\b",
        r"<think>",
        r"(?i)<br\s*/?>",   # ✅ HTML br 금지
        r"(?i)<p\s*>",
        r"(?i)</p\s*>",
        r"(?i)<div\s*>",
        r"(?i)</div\s*>",
        # ✅ 섹션 라벨/구분선 금지 (본문에 그대로 박히는 문제 방지)
        r"요약\s*문장",
        r"배경\s*과\s*맥락",
        r"쟁점\s*과\s*의미",
        r"\b결론\b",
        r"────",
    ])

    t = (title or "").strip()
    b = (body or "").strip()

    if len(t) < min_title_chars:
        fail = _make_fail_preview_html(topic_tag, title, body, f"title too short (<{min_title_chars})")
        raise RuntimeError(f"E_GUARD_TITLE_SHORT: saved={fail}")

    if len(t) > max_title_chars:
        fail = _make_fail_preview_html(topic_tag, title, body, f"title too long (>{max_title_chars})")
        raise RuntimeError(f"E_GUARD_TITLE_LONG: saved={fail}")

    # --- Soft guard: BODY_SHORT ---
    # 한국어 설명:
    # - 기존: min_body_chars 미만이면 무조건 실패(가드 HTML 저장) → 게시 실패가 누적
    # - 변경: 아주 심각하게 짧은 경우만 하드 실패로 처리하고,
    #         그 외는 경고 로그만 남기고 통과(가능하면 발행까지 진행)
    soft_ratio = float(getattr(config, "LLM_GUARD_BODY_SOFT_RATIO", 0.70))
    hard_min = int(getattr(config, "LLM_GUARD_BODY_HARD_MIN", 420))
    soft_min = max(hard_min, int(min_body_chars * soft_ratio))

    if len(b) < min_body_chars:
        # Hard fail only if extremely short
        if len(b) < soft_min:
            print(f"[WARN] Guard: body short. continue...")
        print(f"[WARN] Soft guard: body short (len={len(b)} < {min_body_chars}). continue...")

    # ===== 문단 카운트 강화 =====
    paras_blank = [p.strip() for p in re.split(r"\n\s*\n", b) if p.strip()]

    parts_by_heading = []
    if "##" in b:
        chunks = re.split(r"(?m)^\s*##\s+", b)
        for ch in chunks:
            ch = ch.strip()
            if ch:
                parts_by_heading.append(ch)

    lines = [ln.strip() for ln in b.split("\n") if ln.strip()]
    estimated_by_lines = []
    if len(lines) >= 10:
        step = 5
        for i in range(0, len(lines), step):
            block = "\n".join(lines[i:i + step]).strip()
            if block:
                estimated_by_lines.append(block)

    para_count = max(len(paras_blank), len(parts_by_heading), len(estimated_by_lines))

    # NOTE(KO): 사용자는 "짧아도 통과"를 원함.
    # - 문단 수가 부족하더라도 실패시키지 않고 경고만 남긴다.
    # NOTE(EN): Do not hard-fail on paragraph count; log a warning and continue.
    if min_paragraphs and para_count < min_paragraphs:
        print(
            f"[WARN] Guard: too few paragraphs (<{min_paragraphs}); counted={para_count} "
            f"(blank={len(paras_blank)}, heading={len(parts_by_heading)}, est={len(estimated_by_lines)}). continue..."
        )

    combined = f"{t}\n{b}"

    # ✅ 한자 섞이면 실패 처리 (중국어/한자 출력 방지)
    if _contains_cjk_ideographs(combined):
        fail = _make_fail_preview_html(topic_tag, title, body, "contains CJK ideographs (Chinese characters)")
        raise RuntimeError(f"E_GUARD_LANG_CJK: saved={fail}")

    for pat in banned_patterns:
        if re.search(pat, combined):
            fail = _make_fail_preview_html(topic_tag, title, body, f"banned pattern matched: {pat}")
            raise RuntimeError(f"E_GUARD_BANNED_PATTERN: {pat} saved={fail}")

    brace_count = b.count("{") + b.count("}")
    if brace_count >= 8:
        fail = _make_fail_preview_html(topic_tag, title, body, f"suspicious JSON/braces count ({brace_count})")
        raise RuntimeError(f"E_GUARD_JSON_LEAK: saved={fail}")


def _fallback_title_from_article(article_title: str, max_len: int = 80) -> str:
    t = (article_title or "").strip()
    t = re.sub(r"\s+", " ", t)
    if len(t) > max_len:
        t = t[:max_len].rstrip()
    return t if t else "뉴스 요약"


def generate_post_with_ollama(
    category: str,
    article: dict,
    ollama_url: str,
    model: str,
    timeout: int = 600,
    topic_tag: str = "topic"
):
    import config

    if article.get("link"):
        article["link"] = _resolve_final_url(article["link"])

    endpoint = ollama_url.rstrip("/") + "/api/generate"

    
    schema = {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "summary": {"type": "array", "items": {"type": "string"}},
            "context": {"type": "array", "items": {"type": "string"}},
            "analysis": {"type": "array", "items": {"type": "string"}},
            "conclusion": {"type": "string"},
            "caution": {"type": "string"},
            # fallback fields (모델이 schema를 무시하는 경우 대비)
            "body": {"type": "string"},
            "content": {"type": "string"},
            "article": {"type": "string"},
            "text": {"type": "string"},
        },
        "required": ["title", "summary", "context", "analysis", "conclusion", "caution"]
    }

    base_prompt = build_prompt_json(category, article)
    _write_text(DEBUG_DIR / f"llm_prompt_{topic_tag}_{_now_tag()}.txt", base_prompt)

    base_options = {
        "temperature": getattr(config, "LLM_TEMPERATURE", 0.2),
        "top_p": getattr(config, "LLM_TOP_P", 0.9),
        "num_predict": getattr(config, "LLM_NUM_PREDICT", 1800),
    }

    max_retries = getattr(config, "LLM_MAX_RETRIES", 2)

    def call_ollama(prompt: str, *, fmt, options: dict, mode_tag: str):
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "format": fmt,
            "options": options,
        }

        _write_text(
            DEBUG_DIR / f"llm_payload_{topic_tag}_{mode_tag}_{_now_tag()}.json",
            json.dumps(payload, ensure_ascii=False, indent=2)
        )

        # NOTE(KO): Ollama가 긴 응답에서 멈추거나 모델이 걸리면 requests ReadTimeout이 발생할 수 있음.
        #           이 경우 파이프라인 전체를 중단하지 말고, 상위 로직에서 '기사 스킵' 처리할 수 있도록
        #           RuntimeError로 변환한다.
        # NOTE(EN): Convert ReadTimeout into RuntimeError so the caller can skip the article.
        try:
            r = requests.post(endpoint, json=payload, timeout=(10, timeout))
            r.raise_for_status()
        except requests.exceptions.ReadTimeout as e:
            raise RuntimeError(
                f"E_LLM_TIMEOUT({mode_tag}): ReadTimeout after {timeout}s (ollama={endpoint})"
            ) from e
        except requests.exceptions.ConnectionError as e:
            raise RuntimeError(
                f"E_LLM_CONN({mode_tag}): cannot connect to ollama (ollama={endpoint})"
            ) from e
        data = r.json()
        raw = (data.get("response", "") or "").replace("\ufeff", "").strip()


        raw_path = DEBUG_DIR / f"llm_raw_{topic_tag}_{mode_tag}_{_now_tag()}.txt"
        _write_text(raw_path, raw)

        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = _extract_first_json_object(raw)

        return parsed, raw_path

    last_raw_path = None
    last_mode = None

    parsed = None
    for attempt in range(1, max_retries + 1):
        if attempt == 1:
            mode = "schema"
            prompt = base_prompt
            options = dict(base_options)
            fmt = schema
        else:
            mode = "json_fallback"
            prompt = base_prompt + "\n\nIMPORTANT: Output ONLY valid JSON. No extra text."
            options = dict(base_options)
            options["temperature"] = 0
            options["num_predict"] = max(options.get("num_predict", 1800), 2000)
            fmt = "json"

        parsed, raw_path = call_ollama(prompt, fmt=fmt, options=options, mode_tag=mode)
        last_raw_path = raw_path
        last_mode = mode

        if isinstance(parsed, dict):
            break

    if not isinstance(parsed, dict):
        raise RuntimeError(f"E_LLM_PARSE_FAILED({last_mode}): response not JSON. saved={last_raw_path}")

    title = _clean_weird_lang((parsed.get("title") or "").strip())

    # ✅ LLM이 섹션 라벨을 본문에 박는 문제를 방지하기 위해 구조화 필드에서 조립한다.
    # Assemble from structured fields to avoid label-like outputs in the final body.
    summary = parsed.get("summary") or []
    context = parsed.get("context") or []
    analysis = parsed.get("analysis") or []
    # conclusion can be a string OR a list depending on model output.
    # 리스트가 오면 한 줄 텍스트로 합쳐서 AttributeError("list has no strip")를 방지한다.
    conclusion_v = parsed.get("conclusion")
    if isinstance(conclusion_v, list):
        conclusion = "\n".join([str(x).strip() for x in conclusion_v if str(x).strip()]).strip()
    else:
        conclusion = (conclusion_v or "").strip()

    # ===== 본문 형식 =====
    # 원하는 레이아웃:
    #   (상단 이미지 2장: 제목/요약)  <- tistory_bot에서 처리
    #   요약
    #   ...
    #   §§BODY_IMG§§  (본문 이미지가 삽입될 자리)
    #   본문
    #   ...
    BODY_MARKER = "§§BODY_IMG§§"

    # 1) 구조화 필드에서 '요약/본문' 2단원 형태로 구성
    main_text_parts = []
    main_text_parts.extend(_normalize_paragraphs(context))
    main_text_parts.extend(_normalize_paragraphs(analysis))
    if conclusion:
        main_text_parts.append(conclusion)
    main_text = "\n\n".join([p for p in main_text_parts if (p or '').strip()]).strip()

    body = _format_two_section_body(summary, main_text, BODY_MARKER)

    # 2) ✅ 조립 결과가 비면, LLM이 준 body/content/text 등을 fallback으로 사용
    if not body or not body.strip():
        body = extract_body(parsed)

    # 3) 정리/필터링
    body = _clean_weird_lang(body)
    # Optional: strip excessive English tokens in Korean posts.
    # (Allow product names / acronyms via whitelist.)
    # 한국어 글에서 과도한 영어 토큰 제거(화이트리스트 허용)
    if getattr(config, 'STRIP_ENGLISH_TOKENS', True):
        body = _strip_english_except_whitelist(body)

    body = re.sub(r'^\|\s*\n', '', body).strip()

    # ✅ 출처 링크는 자동화 파이프라인에서 중요한 메타데이터
    # Source link (metadata): helpful for attribution and transparency
    src = article.get("source") or "출처"
    url = article.get("link") or ""
    append_src_url = getattr(config, "APPEND_SOURCE_URL", True)
    if append_src_url and url:
        body = body.rstrip() + f"\n\n출처: {src} ({url})\n"

    # ✅ title이 비거나 너무 짧으면 기사 제목으로 1차 보정
    if not title or len(title.strip()) < getattr(config, "LLM_MIN_TITLE_CHARS", 8):
        title = _fallback_title_from_article(article.get("title", ""), getattr(config, "LLM_MAX_TITLE_CHARS", 80))

    if not body:
        raise RuntimeError(f"E_LLM_BODY_EMPTY({last_mode}): saved={last_raw_path}")

    rewrite_on_short = getattr(config, "LLM_REWRITE_ON_SHORT", True)
    rewrite_max_tries = getattr(config, "LLM_REWRITE_MAX_TRIES", 2)

    # 1) 일단 검증
    try:
        _validate_post_quality(title, body, topic_tag)
        return title, body

    except RuntimeError as e:
        msg = str(e)
        if not rewrite_on_short:
            raise

        # ✅ title 관련 실패면 기사 제목으로 보정하고 재검증
        if "E_GUARD_TITLE_SHORT" in msg or "E_GUARD_TITLE_LONG" in msg:
            title = _fallback_title_from_article(article.get("title", ""), getattr(config, "LLM_MAX_TITLE_CHARS", 80))
            _validate_post_quality(title, body, topic_tag)
            return title, body

        # ✅ 언어/본문/문단 실패면 rewrite
        allowed = (
            ("E_GUARD_BODY_SHORT" in msg) or
            ("E_GUARD_PARA_FEW" in msg) or
            ("E_GUARD_LANG_CJK" in msg) or
            ("E_GUARD_BLOCKS_MISSING" in msg)
        )
        if not allowed:
            raise

        # ✅ rewrite는 '초안'을 주면 오염(한자/잡문자)이 전염되기 쉬움
        # ✅ 그래서 실패 사유만 주고, base_prompt로 처음부터 재생성한다.
        for k in range(rewrite_max_tries):
            rewrite_prompt = _build_retry_prompt_kor(base_prompt, msg)

            options2 = {
                "temperature": 0,
                "top_p": 0.9,
                "num_predict": max(getattr(config, "LLM_REWRITE_NUM_PREDICT", 2200),
                                   getattr(config, "LLM_NUM_PREDICT", 1800)),
            }

            parsed2, raw2_path = call_ollama(
                rewrite_prompt,
                fmt="json",
                options=options2,
                mode_tag=f"rewrite{k+1}"
            )

            if not isinstance(parsed2, dict):
                continue

            title2 = _clean_weird_lang((parsed2.get("title") or "").strip())

            summary2 = parsed2.get("summary") or []
            context2 = parsed2.get("context") or []
            analysis2 = parsed2.get("analysis") or []
            conclusion2_v = parsed2.get("conclusion")
            if isinstance(conclusion2_v, list):
                conclusion2 = "\n".join([str(x).strip() for x in conclusion2_v if str(x).strip()]).strip()
            else:
                conclusion2 = (conclusion2_v or "").strip()

            # rewrite에서도 동일한 '요약/본문' 2단원 + 본문 이미지 마커 유지
            main2_parts = []
            main2_parts.extend(_normalize_paragraphs(context2))
            main2_parts.extend(_normalize_paragraphs(analysis2))
            if conclusion2:
                main2_parts.append(conclusion2)
            main2 = "\n\n".join([p for p in main2_parts if (p or '').strip()]).strip()

            body2 = _format_two_section_body(summary2, main2, BODY_MARKER)

            if not body2 or not body2.strip():
                body2 = extract_body(parsed2)

            body2 = _clean_weird_lang(body2)
            if getattr(config, 'STRIP_ENGLISH_TOKENS', True):
                body2 = _strip_english_except_whitelist(body2)
            body2 = re.sub(r'^\|\s*\n', '', body2).strip()

            if append_src_url and url:
                body2 = body2.rstrip() + f"\n\n출처: {src} ({url})\n"

            if not title2 or len(title2) < getattr(config, "LLM_MIN_TITLE_CHARS", 8):
                title2 = _fallback_title_from_article(article.get("title", ""), getattr(config, "LLM_MAX_TITLE_CHARS", 80))

            if not body2:
                continue

            _validate_post_quality(title2, body2, topic_tag)
            return title2, body2

        raise