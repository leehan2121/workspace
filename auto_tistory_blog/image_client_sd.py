"""image_client_sd.py

썸네일 이미지를 생성하기 위해 Stable Diffusion WebUI(AUTOMATIC1111)의 txt2img API를
호출하는 클라이언트 모듈입니다.

Client module that calls Stable Diffusion WebUI(AUTOMATIC1111) txt2img API to
generate thumbnail images.

왜 바꿨나
- 디버그 로그에 SD 500 에러(NaNsException)가 반복됩니다.
- 서버 설정(--no-half 또는 Upcast 설정)이 최선이지만, 코드에서도 재시도/폴백을 제공하면
  자동화가 끊기지 않습니다.

Why this change
- We observed repeated SD 500 errors (NaNsException).
- Server-side fix is best (--no-half / upcast attention), but retry + fallback
  keeps the automation running.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

try:
    # 폴백 이미지를 로컬에서 생성하기 위해 사용
    # Pillow (PIL): 이미지 처리 라이브러리 (image processing library)
    from PIL import Image, ImageDraw
except Exception:  # pragma: no cover
    Image = None
    ImageDraw = None


DEBUG_DIR = Path("debug")
DEBUG_DIR.mkdir(exist_ok=True)


def _now_tag() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text if text is not None else "")


def _save_png(b64_png: str, out_path: Path) -> None:
    raw = base64.b64decode(b64_png)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "wb") as f:
        f.write(raw)


def _is_nan_error(resp_text: str) -> bool:
    """SD NaN 오류인지 간단 판별.

    Detect SD NaN-related errors.
    - NaN (Not-a-Number): 수치 불안정 (numerical instability)
    """
    if not resp_text:
        return False
    t = resp_text.lower()
    return "nansexception" in t or "tensor with nans" in t


def _make_fallback_thumbnail(out_path: Path, width: int, height: int) -> bool:
    """SD 실패 시, 텍스트 없는 폴백 썸네일 생성.

    Create a textless fallback thumbnail when SD generation fails.
    - fallback (대체): SD가 실패해도 업로드 파이프라인을 유지
    - geometric (기하학): 원/사각형 등 단순 도형 기반
    """
    if Image is None or ImageDraw is None:
        return False

    out_path.parent.mkdir(parents=True, exist_ok=True)

    w, h = int(width), int(height)
    img = Image.new("RGB", (w, h), (245, 245, 245))
    d = ImageDraw.Draw(img)

    pad = max(18, min(w, h) // 18)
    d.rounded_rectangle([pad, pad, w - pad, h - pad], radius=pad, outline=(210, 210, 210), width=4)

    r = int(min(w, h) * 0.18)
    cx, cy = int(w * 0.35), int(h * 0.48)
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=(190, 190, 190), width=8)

    d.rounded_rectangle(
        [int(w * 0.55), int(h * 0.30), int(w * 0.88), int(h * 0.70)],
        radius=pad,
        outline=(195, 195, 195),
        width=8,
    )

    img.save(out_path, format="PNG")
    return True


def sd_txt2img(
    prompt: str,
    negative_prompt: str = "",
    width: int = 768,
    height: int = 512,
    steps: int = 20,
    cfg_scale: float = 7.0,
    sampler_name: Optional[str] = None,
    seed: int = -1,
    sd_base_url: str = "http://127.0.0.1:7860",
    timeout_sec: int = 900,
    out_dir: str = "debug/images",
    file_prefix: str = "cover",
    fallback_on_fail: bool = True,
) -> Optional[str]:
    """Stable Diffusion WebUI(AUTOMATIC1111) /sdapi/v1/txt2img 호출.

    - 서버 에러(500), 잘못된 sampler, OOM 등 어떤 문제든 debug 파일로 원인을 저장
    - NaN 에러는 파라미터를 낮춰 재시도
    - 최종 실패 시 폴백 이미지 생성(옵션)

    Call Stable Diffusion WebUI(AUTOMATIC1111) /sdapi/v1/txt2img.
    - Save errors into debug files
    - Retry with safer params for NaN errors
    - Optionally generate a fallback image
    """

    url = sd_base_url.rstrip("/") + "/sdapi/v1/txt2img"

    out_dir_path = Path(out_dir)
    out_dir_path.mkdir(parents=True, exist_ok=True)

    # 1차/2차 재시도 파라미터 (NaN 안정화 목적)
    # retry (재시도): 동일 요청 실패 시 파라미터를 조정해 다시 시도
    attempts = [
        {"steps": int(steps), "cfg": float(cfg_scale), "w": int(width), "h": int(height)},
        {"steps": max(12, int(steps) - 8), "cfg": max(5.5, float(cfg_scale) - 1.5), "w": min(640, int(width)), "h": min(448, int(height))},
        {"steps": 12, "cfg": 5.5, "w": 512, "h": 384},
    ]

    last_err_path: Optional[Path] = None

    for idx, pset in enumerate(attempts, start=1):
        payload = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
            "width": int(pset["w"]),
            "height": int(pset["h"]),
            "steps": int(pset["steps"]),
            "cfg_scale": float(pset["cfg"]),
            "seed": int(seed),
        }
        if sampler_name:
            payload["sampler_name"] = sampler_name

        req_path = DEBUG_DIR / f"sd_request_{file_prefix}_{_now_tag()}_{idx}.json"
        _write_text(req_path, json.dumps(payload, ensure_ascii=False, indent=2))

        try:
            r = requests.post(url, json=payload, headers={"Content-Type": "application/json"}, timeout=(10, timeout_sec))

            if r.status_code >= 400:
                err_path = DEBUG_DIR / f"sd_error_{file_prefix}_{_now_tag()}_{idx}.txt"
                _write_text(
                    err_path,
                    f"URL: {url}\nSTATUS: {r.status_code}\n\nRESPONSE_TEXT:\n{r.text}\n\nREQUEST_FILE: {req_path}\n",
                )
                last_err_path = err_path

                # NaN이면 다음 파라미터로 재시도
                if r.status_code == 500 and _is_nan_error(r.text):
                    continue
                return None

            data = r.json()

        except Exception as e:
            err_path = DEBUG_DIR / f"sd_exception_{file_prefix}_{_now_tag()}_{idx}.txt"
            _write_text(
                err_path,
                f"URL: {url}\nEXCEPTION: {repr(e)}\nREQUEST_FILE: {req_path}\n",
            )
            last_err_path = err_path
            continue

        images = data.get("images") or []
        if not images:
            empty_path = DEBUG_DIR / f"sd_empty_{file_prefix}_{_now_tag()}_{idx}.txt"
            _write_text(empty_path, f"URL: {url}\nNo images in response.\nRAW:\n{json.dumps(data, ensure_ascii=False)[:5000]}")
            last_err_path = empty_path
            continue

        out_path = out_dir_path / f"{file_prefix}_{_now_tag()}.png"
        _save_png(images[0], out_path)
        return str(out_path)

    # 최종 실패: 폴백 생성
    if fallback_on_fail:
        fb_path = out_dir_path / f"{file_prefix}_fallback_{_now_tag()}.png"
        ok = _make_fallback_thumbnail(fb_path, width=int(width), height=int(height))
        if ok:
            # 원인 파일 링크도 남겨서 추적 가능
            if last_err_path:
                link_path = DEBUG_DIR / f"sd_fallback_note_{file_prefix}_{_now_tag()}.txt"
                _write_text(link_path, f"Fallback image generated: {fb_path}\nLast error file: {last_err_path}\n")
            return str(fb_path)

    return None
