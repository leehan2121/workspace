# tistory_image.py
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC

def _find_file_inputs(driver):
    inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    # 화면에 보이든 숨겨져 있든, send_keys는 보통 먹힘
    return inputs

def upload_and_insert_image(driver, wait, image_path: str, sleep_after_upload: float = 2.5):
    """
    티스토리 글쓰기 화면에서 이미지 업로드 후 본문에 삽입 시도.
    - image_path: 로컬 png/jpg 절대경로 권장
    """
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"E_IMAGE_NOT_FOUND: {image_path}")

    abs_path = str(p.resolve())

    # 1) 에디터에 "이미지/사진" 버튼이 있으면 눌러서 file input을 활성화
    # (없어도 아래 file input 직접 send_keys로 걸리는 경우가 있음)
    candidates = [
        "button[title*='이미지']",
        "button[aria-label*='이미지']",
        "button[title*='사진']",
        "button[aria-label*='사진']",
        "button:has(svg)",  # 일부 에디터는 아이콘 버튼
    ]
    for sel in candidates:
        try:
            btns = driver.find_elements(By.CSS_SELECTOR, sel)
            for b in btns[:3]:
                try:
                    if b.is_displayed() and b.is_enabled():
                        b.click()
                        time.sleep(0.3)
                        raise StopIteration
                except Exception:
                    pass
        except StopIteration:
            break
        except Exception:
            pass

    # 2) file input 찾아서 업로드
    inputs = _find_file_inputs(driver)
    if not inputs:
        # DOM이 늦게 올라오는 경우 대비
        time.sleep(1.0)
        inputs = _find_file_inputs(driver)

    if not inputs:
        raise RuntimeError("E_TISTORY_FILE_INPUT_NOT_FOUND: input[type=file]을 찾지 못했습니다.")

    # 여러 개가 있을 수 있으니, 첫 번째부터 순차 시도
    last_exc = None
    for inp in inputs:
        try:
            inp.send_keys(abs_path)
            last_exc = None
            break
        except Exception as e:
            last_exc = e

    if last_exc:
        raise RuntimeError(f"E_TISTORY_UPLOAD_SENDKEYS_FAILED: {repr(last_exc)}")

    # 3) 업로드/삽입 대기
    time.sleep(sleep_after_upload)

    # 4) “삽입/완료” 같은 버튼이 뜨는 케이스 처리
    insert_btn_selectors = [
        "button:contains('삽입')",
        "button:contains('완료')",
    ]
    # Selenium 기본은 :contains 지원 안 하니까 텍스트 탐색으로 처리
    try:
        buttons = driver.find_elements(By.CSS_SELECTOR, "button")
        for b in buttons:
            try:
                t = (b.text or "").strip()
                if t in ("삽입", "완료"):
                    if b.is_displayed() and b.is_enabled():
                        b.click()
                        time.sleep(0.5)
                        break
            except Exception:
                pass
    except Exception:
        pass

    return True
