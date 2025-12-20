# config.py

# ===== 계정 (요청대로 코드에 유지) =====
KAKAO_ID = "leehan2121@kakao.com"
KAKAO_PW = "fnzktm21@!"

# ===== URL =====
TISTORY_LOGIN_URL = "https://www.tistory.com/auth/login"
TISTORY_WRITE_URL = "https://ohmygodit.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F"

# ===== RSS =====
RSS_URL = "https://news.ycombinator.com/rss"
MAX_ITEMS = 5

# ===== 발행 옵션 =====
# 임시저장 이어쓰기 alert 처리:
# False = 취소(dismiss) -> 새 글로 진행되는 경우가 많음
# True  = 확인(accept) -> 이어서 작성
DRAFT_ALERT_ACCEPT = False

# 발행 레이어 공개 설정 (value 기준)
# 공개: open20 / 보호: open15 / 비공개: open0
VISIBILITY_ID = "open0"   # 지금은 비공개 고정