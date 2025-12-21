# image_pipeline.py
import config
from image_client_sd import sd_txt2img

def build_sd_prompt(topic_key: str, title_text: str) -> str:
    """
    너무 디테일하게 가면 느려지고 실패 확률 올라감.
    빠르고 무난한 '커버 이미지' 스타일로 고정.
    """
    topic_map = {
        "politics": "newspaper editorial illustration",
        "gossip": "celebrity magazine cover style illustration",
        "kpop": "modern pop culture poster illustration",
        "hot": "breaking news cover illustration",
    }
    style = topic_map.get(topic_key, "news cover illustration")

    # 제목을 그대로 넣되, 길면 SD가 산만해져서 한 줄로 압축
    safe_title = (title_text or "").strip().replace("\n", " ")
    if len(safe_title) > 60:
        safe_title = safe_title[:60] + "..."

    return (
        f"{style}, clean typography space, minimal, high quality, "
        f"no watermark, no logo, no text artifacts, "
        f"theme: {topic_key}, headline: {safe_title}"
    )

def build_sd_negative() -> str:
    return (
        "low quality, blurry, watermark, logo, text, letters, "
        "extra fingers, deformed, bad anatomy, jpeg artifacts"
    )

def generate_cover_image(topic_key: str, title_text: str) -> str:
    prompt = build_sd_prompt(topic_key, title_text)
    negative = build_sd_negative()

    # ✅ 기본은 “빨리 1장 뽑기”
    # 느리면 steps를 더 낮추고(15), width/height 줄여라(512x512)
    return sd_txt2img(
        prompt=prompt,
        negative_prompt=negative,
        width=getattr(config, "SD_WIDTH", 768),
        height=getattr(config, "SD_HEIGHT", 512),
        steps=getattr(config, "SD_STEPS", 20),
        cfg_scale=getattr(config, "SD_CFG_SCALE", 7.0),
        sampler_name=getattr(config, "SD_SAMPLER", "DPM++ 2M"),
        seed=-1,
        sd_base_url=getattr(config, "SD_BASE_URL", "http://127.0.0.1:7860"),
        timeout_sec=getattr(config, "SD_TIMEOUT_SEC", 900),
        out_dir=getattr(config, "SD_OUT_DIR", "debug/images"),
        file_prefix=f"{topic_key}_cover",
    )
