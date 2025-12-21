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

    # SD 프롬프트는 영어가 안정적
    prompt = f"{style}, clean composition, high quality, modern, minimal text, headline area, {title_text}"
    negative = "low quality, blurry, watermark, logo, distorted face, gibberish text, extra fingers"

    # 설정 키가 SD_URL / SD_BASE_URL 둘 다 존재할 수 있어서 안전하게 처리
    # Handle both SD_URL and SD_BASE_URL for backward compatibility
    sd_base_url = getattr(config, "SD_URL", None) or getattr(config, "SD_BASE_URL", "http://127.0.0.1:7860")

    # ✅ sampler 기본값을 None으로 (서버에 없는 sampler면 500 발생 가능)
    sampler = getattr(config, "SD_SAMPLER", None)
    if sampler is not None and str(sampler).strip() == "":
        sampler = None

    return sd_txt2img(
        prompt=prompt,
        negative_prompt=negative,
        width=getattr(config, "SD_WIDTH", 768),
        height=getattr(config, "SD_HEIGHT", 512),
        steps=getattr(config, "SD_STEPS", 20),
        cfg_scale=getattr(config, "SD_CFG_SCALE", 7.0),
        sampler_name=sampler,
        seed=-1,
        sd_base_url=sd_base_url,
        timeout_sec=getattr(config, "SD_TIMEOUT_SEC", 900),
        out_dir=getattr(config, "SD_OUT_DIR", "debug/images"),
        file_prefix=f"{topic_key}_cover",
    )
