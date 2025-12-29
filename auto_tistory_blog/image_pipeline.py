# image_pipeline.py
import config
import re
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
    # NOTE(KO): 이미지 안에 알수없는 문자/외계어가 찍히는 경우가 많아
    #           '텍스트 없음'을 강하게 유도하고 negative에도 text 관련 토큰을 강화.
    # NOTE(EN): Strongly discourage any text/letters in the image.
    prompt = f"{style}, clean composition, high quality, modern, no text, no letters, minimal typography, headline area, {title_text}"
    negative = "text, letters, words, watermark, logo, caption, subtitle, gibberish, symbols, low quality, blurry, distorted face, extra fingers"

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



def build_sd_prompt_for_section(topic_key: str, title_text: str, section_text: str, kind: str) -> str:
        """
        # 섹션(요약/배경·맥락)용 이미지 생성
        # Build a section image (summary/context) for the post.

        kind:
          - "summary": 요약 위
          - "body": 본문 위 (요약/본문 사이 마커 위치)
        """
        sd_base_url = (getattr(config, "SD_URL", None) or getattr(config, "SD_BASE_URL", None) or "http://127.0.0.1:7860")

        # 핵심 텍스트만 잘라 사용 (너무 길면 SD가 산으로 감)
        raw = (section_text or "").strip()
        raw = re.sub(r"\s+", " ", raw)
        raw = raw[:180]

        # 토픽/섹션별 스타일을 약간만 분기 (과도한 변화는 금지)
        topic_map = {
            "politics": "newspaper editorial illustration, documentary photo style, neutral tone",
            "gossip": "magazine style illustration, editorial layout",
            "kpop": "modern pop culture poster illustration",
            "hot": "breaking news cover illustration",
        }
        base_style = topic_map.get(topic_key, "news editorial illustration")

        if kind == "summary":
            style = f"{base_style}, headline banner"
            file_prefix = f"{topic_key}_summary"
        elif kind == "body":
            style = f"{base_style}, context scene, neutral illustration, no text"
            file_prefix = f"{topic_key}_body"
        else:
            style = f"{base_style}"
            file_prefix = f"{topic_key}_{kind}"

        # 본문과 연결성을 높이기 위해 타이틀 + 핵심문장 일부를 포함
        prompt = f"{style}, Korean news topic, no text, no letters. Title: {title_text}. Key points: {raw}"

        # 사람/얼굴이 튀는 걸 줄이기 위해 강하게 억제
        negative = (
            "nsfw, nude, porn, "
            "portrait, face, person, people, human, selfie, "
            "anime, manga, cartoon, "
            "text, letters, words, watermark, logo, caption, subtitle, gibberish, symbols, "
            "blurry, low quality"
        )

        sampler = getattr(config, "SD_SAMPLER", "Euler a")

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
            file_prefix=file_prefix,
        )
