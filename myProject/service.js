//  이미지 처리 함수
//  hyunilPark
//  leehan2121@gmail.com

// multer : multipart/form-data(파일 업로드)를 처리하는 미들웨어
const multer = require('multer');

// path : 파일 경로, 확장자 처리용 Node 기본 모듈
const path = require('path');

// fs : 파일 시스템 접근 (폴더 존재 여부 확인, 생성)
const fs = require('fs');

/**
 * 업로드된 파일이 저장될 실제 디렉토리 경로
 * __dirname : 현재 파일이 위치한 폴더
 */
const uploadDir = path.join(__dirname, 'uploads');

/**
 * uploads 폴더가 존재하지 않으면 생성
 * - 서버 첫 실행 시 필수
 * - 운영 환경에서 서버 크래시 방지
 */
if (!fs.existsSync(uploadDir)) {
  fs.mkdirSync(uploadDir);
}

/**
 * multer 저장소(storage) 설정
 * - 어디에(destination)
 * - 어떤 이름으로(filename)
 * 파일을 저장할지 정의
 */
const storage = multer.diskStorage({

  /**
   * 파일 저장 위치 지정
   * cb(error, destinationPath)
   */
  destination: (req, file, cb) => {
    cb(null, uploadDir);
  },

  /**
   * 서버에 저장될 파일명 결정
   * - 원본 이름 그대로 쓰면 덮어쓰기 위험 있음
   * - Date.now()로 유니크한 이름 생성
   */
  filename: (req, file, cb) => {
    // 원본 파일의 확장자 추출 (.jpg, .png 등)
    const ext = path.extname(file.originalname);

    // 현재 시간(ms) 기반의 고유 파일명 생성
    const uniqueName = Date.now() + ext;

    // 최종 파일명 전달
    cb(null, uniqueName);
  }
});

/**
 * multer 인스턴스 생성
 * 이 upload 객체를 라우터에서 사용함
 */
const upload = multer({ storage });

/**
 * 외부에서 사용할 수 있도록 export
 * routes.js 등에서 require 해서 사용
 */
module.exports = { upload };