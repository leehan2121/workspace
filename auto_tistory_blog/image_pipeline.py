# image_pipeline.py
import config
from image_client_sd import sd_txt2img

def build_sd_prompt(topic_key: str, title_text: str) -> str:
    """
    빠르고 무난한 '커버 이미지' 스타일로 고정.
    """
    topic_map = {
        "politics": "newspaper editorial illustration",
        "gossip": "celebrity magazine cover style illustration",
        "kpop": "modern pop culture poster illustration",
        "hot": "breaking news cover illustration",
    }
    style = topic_map.get(topic_key, "news cover illustration")

    title = (title_text or "").strip()
    if len(title) > 80:
        title = title[:80].rstrip()

    prompt = f"{style}, clean composition, high detail, readable, {title}"
    negative = "text watermark, logo, low quality, blurry, deformed, extra fingers, bad anatomy"

    # ✅ config.SD_URL 사용하도록 정리 (기존 SD_BASE_URL 혼선 해결)
    sd_base_url = getattr(config, "SD_URL", "http://127.0.0.1:7860")

    return sd_txt2img(
        prompt=prompt,
        negative_prompt=negative,
        width=getattr(config, "SD_WIDTH", 768),
        height=getattr(config, "SD_HEIGHT", 512),
        steps=getattr(config, "SD_STEPS", 20),
        cfg_scale=getattr(config, "SD_CFG_SCALE", 7.0),
        sampler_name=getattr(config, "SD_SAMPLER", "DPM++ 2M"),
        seed=-1,
        sd_base_url=sd_base_url,
        timeout_sec=getattr(config, "SD_TIMEOUT_SEC", 900),
        out_dir=getattr(config, "SD_OUT_DIR", "debug/images"),
        file_prefix=f"{topic_key}_cover",
    )
