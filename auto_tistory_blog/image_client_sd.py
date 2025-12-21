# image_client_sd.py
import base64
from pathlib import Path
from datetime import datetime
import requests
import json

def _now():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def sd_txt2img(
    prompt: str,
    negative_prompt: str = "",
    width: int = 768,
    height: int = 512,
    steps: int = 20,
    cfg_scale: float = 7.0,
    sampler_name: str = "DPM++ 2M",
    seed: int = -1,
    sd_base_url: str = "http://127.0.0.1:7860",
    timeout_sec: int = 900,
    out_dir: str = "debug/images",
    file_prefix: str = "cover",
):
    """
    Stable Diffusion WebUI(AUTOMATIC1111) txt2img 호출 후 PNG 저장.
    - timeout_sec: 생성이 느릴 수 있으니 넉넉히(기본 900초)
    """
    endpoint = sd_base_url.rstrip("/") + "/sdapi/v1/txt2img"

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": int(width),
        "height": int(height),
        "steps": int(steps),
        "cfg_scale": float(cfg_scale),
        "sampler_name": sampler_name,
        "seed": int(seed),
        "batch_size": 1,
        "n_iter": 1,
    }

    # 요청/응답 디버그 저장(원인 추적용)
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    req_log = out_path / f"{file_prefix}_{_now()}_request.json"
    with open(req_log, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    r = requests.post(endpoint, json=payload, timeout=(15, timeout_sec))
    r.raise_for_status()
    data = r.json()

    if "images" not in data or not data["images"]:
        raise RuntimeError("E_SD_NO_IMAGES: txt2img 응답에 images가 없습니다.")

    # images[0]는 base64 PNG (data:image/png;base64,... 형태일 수도 있음)
    b64 = data["images"][0]
    if "," in b64:
        b64 = b64.split(",", 1)[1]

    png_bytes = base64.b64decode(b64)

    img_file = out_path / f"{file_prefix}_{_now()}.png"
    with open(img_file, "wb") as f:
        f.write(png_bytes)

    # 응답 일부 저장
    resp_log = out_path / f"{file_prefix}_{_now()}_response.json"
    try:
        with open(resp_log, "w", encoding="utf-8") as f:
            json.dump({k: data.get(k) for k in ["parameters", "info"]}, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    return str(img_file)
