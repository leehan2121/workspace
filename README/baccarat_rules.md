baccarat/
│
├─ main.py                 # 프로그램 시작점 (Tkinter 실행)
│
├─ gui/
│   ├─ __init__.py
│   ├─ app.py              # 메인 윈도우 / 프레임 관리
│   ├─ table.py            # 카드 테이블 UI
│   ├─ controls.py         # 버튼 (베팅, 다음게임 등)
│   ├─ animations.py       # 카드 딜레이, 순차 공개
│
├─ game/
│   ├─ __init__.py
│   ├─ engine.py           # 기존 play_round 로직
│   ├─ deck.py
│   ├─ rules.py
│
├─ models/
│   ├─ __init__.py
│   ├─ bankroll.py
│
├─ logger/
│   ├─ __init__.py
│   └─ logger.py
│
└─ assets/
    └─ cards/              # 카드 이미지 (png)
    
    
① 게임 시작

잔액 표시

“베팅하세요”

② 베팅

금액 선택 (지금은 고정값도 OK)

PLAYER / BANKER / TIE 중 선택

베팅 확정

👉 이 시점까지는 카드 없음

③ 카드 분배

PLAYER 2장

BANKER 2장

화면에 보여줌

④ 내추럴 체크

자연승이면 → 바로 결과

⑤ 3rd 카드 룰

PLAYER → BANKER 순서로 카드

추가 카드가 있다면 보여줌

⑥ 승자 결정

PLAYER / BANKER / TIE

⑦ 정산

플레이어 돈 증감

카지노 돈 증감

⑧ 결과 표시

승자

배당

현재 잔액

⑨ 다음 게임?

계속 / 종료