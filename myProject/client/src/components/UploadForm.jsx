import axios from 'axios';
import { useState } from 'react';

function UploadForm({ onUploadSuccess }){
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if(!file) return alert('이미지를 선택하세요');

        const formData = new FormData();
        formData.append('image' , file);

        try{
            setLoading(true);

            const res = await axios.post(
                'http://192.168.0.57:3000/api/upload',
                formData
            );

            onUploadSuccess(res.data.url);
        } catch (err) {
            alert('업로드 실패');
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <form onSubmit={handleSubmit}>
            <input type="file" accept="image/*" onChange={(e) => setFile(e.target.files[0])} />
            <br/><br/>
            <button type="submit" disabled={loading}>
                {loading ? '업로드 중...' : '업로드'}
            </button>
        </form>
    )
}