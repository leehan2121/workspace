// ==============================
// API 라우팅 파일
// 작성자: hyunilPark
// ==============================

// express 불러오기
const express = require('express');

// Router 객체 생성
// → 이 파일은 "라우터 모듈" 역할
const router = express.Router();

// multer 설정이 들어있는 upload 미들웨어 불러오기
// service.js에서 export한 upload
const { upload } = require('./service');

/**
 * POST /upload
 * 이미지 파일 업로드 API
 *
 * 요청 형식:
 * - multipart/form-data
 * - field name: image
 */
router.post(
  '/upload',

  // ⬇️ 미들웨어
  // 업로드된 파일을 처리하고
  // req.file 객체를 만들어줌
  upload.single('image'),

  // ⬇️ 최종 라우터 핸들러
  (req, res) => {

    // 파일이 없을 경우 (방어 코드)
    if (!req.file) {
      return res.status(400).json({
        error: 'No file uploaded'
      });
    }

    // 업로드 성공 시 클라이언트에 반환할 데이터
    // ⚠️ 템플릿 문자열은 반드시 백틱(`) 사용
    res.json({
      url: `http://192.168.0.57:3000/uploads/${req.file.filename}`
    });
  }
);

// 외부(server.js)에서 사용 가능하도록 export
module.exports = router;