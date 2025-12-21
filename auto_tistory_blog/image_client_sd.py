# image_client_sd.py
import base64
import requests
from pathlib import Path
from datetime import datetime

def _ts():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def sd_txt2img(
    prompt: str,
    out_dir: str = "assets",
    width: int = 1024,
    height: int = 576,
    steps: int = 25,
    cfg_scale: float = 6.5,
    sd_url: str = "http://127.0.0.1:7860",
    timeout_sec: int = 180
) -> str:
    """
    A1111 Stable Diffusion WebUI API(txt2img) 호출 → PNG 저장 → 파일경로 반환
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)

    payload = {
        "prompt": prompt,
        "negative_prompt": "text, watermark, logo, signature, low quality, blurry",
        "width": width,
        "height": height,
        "steps": steps,
        "cfg_scale": cfg_scale,
    }

    r = requests.post(f"{sd_url.rstrip('/')}/sdapi/v1/txt2img", json=payload, timeout=(15, timeout_sec))
    r.raise_for_status()
    j = r.json()

    if not j.get("images"):
        raise RuntimeError("SD_API_EMPTY: txt2img 응답에 images가 없습니다.")

    img_b64 = j["images"][0]
    img_bytes = base64.b64decode(img_b64)

    path = Path(out_dir) / f"{_ts()}_thumb.png"
    path.write_bytes(img_bytes)
    return str(path)

def build_sd_prompt(topic_key: str, title: str) -> str:
    """
    저작권/인물/로고 리스크 줄이는 “뉴스 썸네일 상징 일러스트” 프롬프트.
    텍스트 없는 이미지로 가는 게 가장 안정적.
    """
    topic_hint = {
        "politics": "정치, 국회, 정책, 토론, 중립적 상징",
        "gossip": "연예, 문화, 행사, 조명, 무대, 중립적 상징",
        "social": "사회, 안전, 사건, 법, 공공, 중립적 상징",
        "kpop": "음악, 공연, 팬, 스테이지, 네온 조명, 중립적 상징",
        "hot": "속보, 이슈, 헤드라인, 알림, 중립적 상징",
    }.get(topic_key, "뉴스, 이슈, 중립적 상징")

    return f"""
뉴스 블로그 썸네일용 일러스트.
주제 힌트: {topic_hint}
기사 제목: {title}

스타일: clean flat illustration, modern editorial illustration, soft lighting, high resolution
구성: 중앙에 상징적인 오브젝트 1~2개 + 단순 배경, 텍스트 없음, 로고 없음
금지: 실존 인물 사진 느낌 금지, 워터마크/서명/글자 금지, 브랜드 로고 금지
""".strip()
