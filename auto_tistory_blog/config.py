# config.py

# ===== 계정 =====
KAKAO_ID = "leehan2121@kakao.com"
KAKAO_PW = "fnzktm21@!"

# ===== URL =====
TISTORY_LOGIN_URL = "https://www.tistory.com/auth/login"
TISTORY_WRITE_URL = "https://ohmygodit.tistory.com/manage/newpost/?type=post&returnURL=%2Fmanage%2Fposts%2F"

# ===== 발행 옵션 =====
DRAFT_ALERT_ACCEPT = False
VISIBILITY_ID = "open0"   # 비공개 고정

# ===== 이미지 옵션 =====
REQUIRE_IMAGE_UPLOAD = False  # 이미지 실패 시 글 발행을 계속할지 여부

# ===== LLM 모드 =====
USE_LLM = True
OLLAMA_URL = "http://127.0.0.1:11434"
OLLAMA_MODEL = "llama3.2:3b"     # 네가 설치한 모델명과 동일해야 함
OLLAMA_MODEL = "llama3.2:3b"
LLM_TIMEOUT = 1200          # 20분 (처음엔 넉넉히)
# LLM 길이 안정화 (짧게 끊기는 문제 방지)
LLM_TEMPERATURE = 0.2
LLM_TOP_P = 0.9
LLM_NUM_PREDICT = 1800
LLM_MAX_RETRIES = 2


# 가드 기준 (지금 프롬프트는 900자 이상 목표라 가드는 유지해도 됨)
LLM_MIN_BODY_CHARS = 450
LLM_MIN_PARAGRAPHS = 3
# 짧으면 리라이트(너가 이미 generator에 넣은 기능이 있을 때만 의미 있음)
LLM_REWRITE_ON_SHORT = True
LLM_REWRITE_MAX_TRIES = 1
LLM_REWRITE_NUM_PREDICT = 2200

# ===== Google News RSS (4개 주제) =====
GOOGLE_NEWS_REGION = "hl=ko&gl=KR&ceid=KR:ko"
GOOGLE_NEWS_LIMIT_PER_TOPIC = 1   # 각 주제당 1개씩만 발행(테스트 목적)

# RSS에서 "가져오는 기사 개수"(후보 풀). 최소 ARTICLE_MAX_TRIES_PER_TOPIC 이상으로 잡아야 함
GOOGLE_NEWS_FETCH_LIMIT_PER_TOPIC = 5

# 한 토픽에서 LLM 실패 시 다음 기사로 넘어가며 최대 몇 개 기사까지 시도할지
ARTICLE_MAX_TRIES_PER_TOPIC = 2

GOOGLE_NEWS_FEEDS = {
    # 최근 1일(when:1d)
    "politics": f"https://news.google.com/rss/search?q=%EC%A0%95%EC%B9%98%20when%3A1d&{GOOGLE_NEWS_REGION}",
    "gossip":   f"https://news.google.com/rss/search?q=%EC%97%B4%EC%95%A0%20OR%20%EC%97%B0%EC%95%A0%20when%3A1d&{GOOGLE_NEWS_REGION}",
    "kpop":     f"https://news.google.com/rss/search?q=KPOP%20OR%20%EC%BC%80%EC%9D%B4%ED%8C%9D%20when%3A1d&{GOOGLE_NEWS_REGION}",
    "hot":      f"https://news.google.com/rss/search?q=%EC%9D%B4%EC%8A%88%20OR%20%EB%85%BC%EB%9E%80%20OR%20%EC%86%8D%EB%B3%B4%20when%3A1d&{GOOGLE_NEWS_REGION}",
}

# prompts.py의 카테고리 키와 맞춰야 함: politics/gossip/social
# hot, kpop은 gossip 또는 social로 매핑해서 사용
PROMPT_CATEGORY_MAP = {
    "politics": "politics",
    "gossip":   "gossip",
    "kpop":     "gossip",
    "hot":      "social",
}

# ===== (선택) RSS 원문(XML) 상단 출력 =====
DEBUG_PRINT_RSS_SOURCE = False

# ===== 기사 단서 추출 (품질 개선) =====
# RSS가 제목/링크만 주는 경우가 많아서, LLM이 쓸 '재료'를 추가로 확보한다.
# Article hint extraction: collects meta description + paragraph snippets.
ENABLE_ARTICLE_HINT = True
ARTICLE_HINT_TIMEOUT_SEC = 12

# ===== 본문 끝 출처 라인 추가 여부 =====
# 출처 표시(attribution)를 자동으로 붙일지 여부
APPEND_SOURCE_URL = True

# === SD(A1111) 이미지 생성/업로드 ===
ENABLE_IMAGE = True

# SD WebUI 주소 (둘 중 하나만)
SD_URL = "http://127.0.0.1:7860"

# 성공률 우선 기본값
SD_WIDTH = 768
SD_HEIGHT = 512
SD_STEPS = 18
SD_CFG_SCALE = 7.0

# sampler는 SD에 없는 이름이면 500 나기 쉬움 → 기본은 None 추천
SD_SAMPLER = None

# 생성 타임아웃 / 저장 경로
SD_TIMEOUT_SEC = 900
SD_OUT_DIR = "debug/images"
