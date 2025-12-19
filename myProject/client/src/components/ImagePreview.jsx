import React, { useState } from 'react';

function ImagePreview() {
  const [image, setImage] = useState(null);      // 선택한 이미지 파일
  const [preview, setPreview] = useState(null);  // 브라우저 미리보기 URL

  // 파일 선택 시 실행
  const handleFileChange = (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setImage(file);
    setPreview(URL.createObjectURL(file)); // 로컬에서 미리보기
  };

  // 업로드 버튼 클릭 시 실행
  const handleUpload = async () => {
    if (!image) {
      alert('먼저 이미지를 선택해주세요!');
      return;
    }

    const formData = new FormData();
    formData.append('image', image);

    try {
      const res = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      });

      if (res.ok) {
        alert('이미지 업로드 성공!');
        setImage(null);
        setPreview(null);
      } else {
        alert('업로드 실패!');
      }
    } catch (err) {
      console.error('업로드 중 에러:', err);
      alert('서버 오류 발생!');
    }
  };

  return (
    <div style={{ padding: '20px' }}>
      <input type="file" accept="image/*" onChange={handleFileChange} />
      {preview && (
        <div style={{ marginTop: '10px' }}>
          <img src={preview} alt="Preview" style={{ width: '200px', height: 'auto' }} />
        </div>
      )}
      <button 
        onClick={handleUpload} 
        style={{ marginTop: '10px', padding: '5px 15px', cursor: 'pointer' }}
      >
        업로드
      </button>
    </div>
  );
}

export default ImagePreview;