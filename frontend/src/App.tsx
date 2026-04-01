import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/layout/Layout';
import UploadPage from './pages/UploadPage';
import JobStatusPage from './pages/JobStatusPage';
import HistoryPage from './pages/HistoryPage';
import TestSkeletonPage from './pages/TestSkeletonPage';

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/jobs/:jobId" element={<JobStatusPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/test" element={<TestSkeletonPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}

export default App;
