# image_client_sd.py
import base64
import json
import time
from pathlib import Path
from datetime import datetime
import requests

DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)
IMG_DIR_DEFAULT = DEBUG_DIR / "images"
IMG_DIR_DEFAULT.mkdir(parents=True, exist_ok=True)

def _now_tag():
    return datetime.now().strftime("%Y%m%d_%H%M%S")

def _write_text(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)

def _save_png(b64_png: str, out_path: Path):
    raw = base64.b64decode(b64_png)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(raw)

def sd_txt2img(
    prompt: str,
    negative_prompt: str = "",
    width: int = 768,
    height: int = 512,
    steps: int = 20,
    cfg_scale: float = 7.0,
    sampler_name: str | None = None,
    seed: int = -1,
    sd_base_url: str = "http://127.0.0.1:7860",
    timeout_sec: int = 900,
    out_dir: str = "debug/images",
    file_prefix: str = "cover",
):
    """
    Stable Diffusion WebUI(AUTOMATIC1111) /sdapi/v1/txt2img 호출
    ✅ 500 에러 시 response.text를 debug로 저장해 원인 추적 가능
    """

    url = sd_base_url.rstrip("/") + "/sdapi/v1/txt2img"

    payload = {
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "width": int(width),
        "height": int(height),
        "steps": int(steps),
        "cfg_scale": float(cfg_scale),
        "seed": int(seed),
    }

    # sampler_name이 잘못되면 SD 내부에서 에러나는 경우가 많아서
    # 값이 있으면 넣고, 없으면 아예 payload에서 제외
    if sampler_name:
        payload["sampler_name"] = sampler_name

    headers = {"Content-Type": "application/json"}

    # 디버그: 요청 저장
    req_path = DEBUG_DIR / f"sd_request_{file_prefix}_{_now_tag()}.json"
    _write_text(req_path, json.dumps(payload, ensure_ascii=False, indent=2))

    try:
        r = requests.post(url, json=payload, headers=headers, timeout=(10, timeout_sec))
        if r.status_code >= 400:
            # ✅ SD가 뱉은 에러 메시지(진짜 원인)가 여기 있음
            err_path = DEBUG_DIR / f"sd_error_{file_prefix}_{_now_tag()}.txt"
            _write_text(
                err_path,
                f"URL: {url}\n"
                f"STATUS: {r.status_code}\n\n"
                f"RESPONSE_TEXT:\n{r.text}\n\n"
                f"REQUEST_FILE: {req_path}\n"
            )
            r.raise_for_status()

        data = r.json()

    except Exception as e:
        # 네트워크/타임아웃/JSON 파싱 문제 등
        err_path = DEBUG_DIR / f"sd_exception_{file_prefix}_{_now_tag()}.txt"
        _write_text(
            err_path,
            f"URL: {url}\n"
            f"EXCEPTION: {repr(e)}\n"
            f"REQUEST_FILE: {req_path}\n"
        )
        raise

    images = data.get("images") or []
    if not images:
        # SD가 200 줬는데 images가 비면 이것도 기록
        empty_path = DEBUG_DIR / f"sd_empty_{file_prefix}_{_now_tag()}.txt"
        _write_text(empty_path, f"URL: {url}\nNo images in response.\nRAW:\n{json.dumps(data, ensure_ascii=False)[:5000]}")
        return None

    out_dir_path = Path(out_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)
    out_path = out_dir_path / f"{file_prefix}_{_now_tag()}.png"
    _save_png(images[0], out_path)
    return str(out_path)
