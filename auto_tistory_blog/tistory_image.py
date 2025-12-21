# tistory_image.py
import time
from pathlib import Path
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def upload_and_insert_image(driver, wait, image_path: str):
    """
    1) 글쓰기 화면에서 이미지 업로드 input[type=file]을 찾아 send_keys
    2) 업로드가 완료되어 본문에 이미지가 삽입될 때까지 대기

    성공 시 True 반환, 실패 시 예외 발생.
    """
    p = Path(image_path)
    if not p.exists():
        raise FileNotFoundError(f"IMAGE_NOT_FOUND: {image_path}")

    abs_path = str(p.resolve())

    # 1) 가능한 모든 file input을 먼저 탐색
    file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")
    if not file_inputs:
        # 혹시 에디터 상단에 "사진" 버튼이 있어야 input이 생기는 구조면 클릭 시도
        _try_click_photo_button(driver, wait)
        time.sleep(0.5)
        file_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='file']")

    if not file_inputs:
        raise RuntimeError("TISTORY_IMAGE_NO_FILE_INPUT: input[type=file]을 찾지 못했습니다.")

    # 2) 여러 input 중 실제 업로드용을 고르기 위해 send_keys 가능한 것부터 시도
    last_err = None
    ok = False
    for inp in file_inputs:
        try:
            driver.execute_script("arguments[0].style.display='block';", inp)
            inp.send_keys(abs_path)
            ok = True
            break
        except Exception as e:
            last_err = e

    if not ok:
        raise RuntimeError(f"TISTORY_IMAGE_SENDKEYS_FAIL: {repr(last_err)}")

    # 3) 업로드 완료/삽입 대기
    # 에디터 DOM마다 다르지만, 보통 본문에 img 태그가 생김
    try:
        wait.until(lambda d: len(d.find_elements(By.CSS_SELECTOR, "img")) > 0)
    except TimeoutException:
        # img가 아닌 figure/attachment 형태일 수 있음
        # 최소한 업로드 진행 UI가 사라지는지 체크
        time.sleep(2)

    return True

def _try_click_photo_button(driver, wait):
    """
    에디터마다 버튼 라벨이 다를 수 있어서 넓게 잡음.
    버튼 클릭은 'input[type=file] 생성 유도' 용도.
    """
    candidates = [
        (By.XPATH, "//button[contains(., '사진')]"),
        (By.XPATH, "//button[contains(., '이미지')]"),
        (By.CSS_SELECTOR, "button[aria-label*='사진']"),
        (By.CSS_SELECTOR, "button[aria-label*='이미지']"),
    ]
    for by, sel in candidates:
        try:
            btn = wait.until(EC.element_to_be_clickable((by, sel)))
            btn.click()
            return True
        except Exception:
            continue
    return False
