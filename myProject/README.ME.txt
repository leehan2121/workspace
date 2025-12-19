React Frontend
┌───────────────────┐
│ UploadForm.jsx    │  <- 이미지 선택, 업로드 버튼
│ ImagePreview.jsx  │  <- 업로드 전 미리보기
│ App.jsx           │  <- 라우팅, 전체 UI 관리
└───────────────────┘
          │ POST /upload
          ▼
Node.js Backend
┌───────────────────┐
│ server.js         │  <- Express 서버 시작
│ service.js        │  <- 파일 처리, 업로드 로직
│ routes.js         │  <- API 라우팅 정리
└───────────────────┘
          │ fs / multer
          ▼
Storage
┌───────────────────┐
│ uploads/          │  <- 서버에 저장된 이미지
└───────────────────┘

React → Node.js API /upload 호출

Node.js → multer 같은 미들웨어로 이미지 받고, uploads/에 저장

저장 성공 → React에서 미리보기/목록 갱신


myProject/
├─ server.js           # Node 메인 서버
├─ service.js          # 이미지 처리 함수
├─ routes.js           # API 라우팅
├─ package.json
├─ uploads/            # 이미지 저장 폴더
└─ client/             # React 프론트
   ├─ public/
   └─ src/
       ├─ App.jsx
       ├─ components/
       │   ├─ UploadForm.jsx
       │   └─ ImagePreview.jsx
       └─ index.js


[ Browser (React UI) ]
        |
        |  POST /api/upload (multipart/form-data)
        v
[ Node.js + Express ]
        |
        |  multer
        v
[ uploads/ 폴더 ]       