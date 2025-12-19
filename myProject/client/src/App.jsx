import { useState } from 'react';
import UploadForm from './components/UploadForm';
import ImagePreview from './components/ImagePreview';

function App() {
  const [imageUrl, setImageUrl] = useState(null);

  return (
    <div style={{ padding: 40 }}>
      <h2>📸 Image Upload Service</h2>

      <UploadForm onUploadSuccess={setImageUrl} />

      {imageUrl && <ImagePreview url={imageUrl} />}
    </div>
  );
}

export default App;
