import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AppProvider } from './stores/AppContext';
import { ConfigProvider } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import HomePage from './pages/HomePage';
import StartPage from './pages/StartPage';
import UploadPage from './pages/UploadPage';
import SummaryPage from './pages/SummaryPage';
import ClusterPage from './pages/ClusterPage';
import PlanPage from './pages/PlanPage';
import GeneratePage from './pages/GeneratePage';
import ResultPage from './pages/ResultPage';
import Layout from './components/Layout';

const antdTheme = {
  token: {
    colorPrimary: '#2F54EB',
    colorSuccess: '#52C41A',
    colorWarning: '#FA8C16',
    colorError: '#FF4D4F',
    colorInfo: '#13C2C2',
    fontSize: 14,
    borderRadius: 6,
  },
};

function App() {
  return (
    <ConfigProvider locale={zhCN} theme={antdTheme}>
      <AppProvider>
        <Router>
          <Routes>
            <Route path="/" element={<HomePage />} />
            <Route path="/start" element={<StartPage />} />
            <Route path="/" element={<Layout />}>
              <Route path="upload" element={<UploadPage />} />
              <Route path="summary" element={<SummaryPage />} />
              <Route path="cluster" element={<ClusterPage />} />
              <Route path="plan" element={<PlanPage />} />
              <Route path="generate" element={<GeneratePage />} />
              <Route path="result" element={<ResultPage />} />
            </Route>
          </Routes>
        </Router>
      </AppProvider>
    </ConfigProvider>
  );
}

export default App;