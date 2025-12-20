# utils.py
import time
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

def pause_forever(driver, msg: str):
    print("⛔ 멈춤:", msg)
    try:
        if driver:
            print("현재 URL:", driver.current_url)
            print("페이지 제목:", driver.title)
    except Exception:
        pass
    while True:
        time.sleep(1)

def handle_any_alert(driver, accept=True, timeout=2):
    """
    떠 있는 alert가 있으면 텍스트 출력 후 처리.
    """
    try:
        WebDriverWait(driver, timeout).until(EC.alert_is_present())
        a = driver.switch_to.alert
        print("⚠️ ALERT 감지:", a.text)
        if accept:
            a.accept()
            print("✅ ALERT 처리: 확인(accept)")
        else:
            a.dismiss()
            print("✅ ALERT 처리: 취소(dismiss)")
        time.sleep(1)
        return True
    except TimeoutException:
        return False
    except Exception as e:
        print("⚠️ ALERT 처리 중 예외:", repr(e))
        return False
