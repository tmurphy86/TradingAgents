import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import NewRunPage from './pages/NewRunPage';
import RunPage from './pages/RunPage';
import HistoryPage from './pages/HistoryPage';
import WatchlistsPage from './pages/WatchlistsPage';

export default function App() {
  return (
    <BrowserRouter>
      <Layout>
        <Routes>
          <Route path="/" element={<Navigate to="/new" replace />} />
          <Route path="/new" element={<NewRunPage />} />
          <Route path="/runs/:runId" element={<RunPage />} />
          <Route path="/history" element={<HistoryPage />} />
          <Route path="/watchlists" element={<WatchlistsPage />} />
        </Routes>
      </Layout>
    </BrowserRouter>
  );
}
