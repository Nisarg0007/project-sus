import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, useNavigate } from 'react-router-dom';
import { InvestigationProvider } from './context/InvestigationContext';
import { Layout } from './components/layout/Layout';
import { CommandPalette } from './components/shared/CommandPalette';
import MissionControl from './pages/MissionControl';
import Activity from './pages/Activity';
import Incidents from './pages/Incidents';
import Merchants from './pages/Merchants';
import InvestigationDetailPage from './pages/InvestigationDetailPage';
import InvestigationHistoryPage from './pages/InvestigationHistoryPage';
import ComparisonPage from './pages/ComparisonPage';
import InvestigationAnalyticsPage from './pages/InvestigationAnalyticsPage';

function App() {
  return (
    <Router>
      <InvestigationProvider>
        <AppContent />
      </InvestigationProvider>
    </Router>
  );
}

function AppContent() {
  const [paletteOpen, setPaletteOpen] = useState(false);
  const navigate = useNavigate();

  // Global keyboard shortcut for command palette
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setPaletteOpen(prev => !prev);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, []);

  return (
    <>
      <Layout>
        <Routes>
          <Route path="/" element={<MissionControl />} />
          <Route path="/activity" element={<Activity />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/merchants" element={<Merchants />} />
          <Route path="/analytics" element={<InvestigationAnalyticsPage />} />
          <Route path="/investigations" element={<InvestigationHistoryPage />} />
          <Route path="/investigations/compare" element={<ComparisonPage />} />
          <Route path="/investigations/:investigationId" element={<InvestigationDetailPage />} />
        </Routes>
      </Layout>
      <CommandPalette
        isOpen={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onNavigate={(path) => {
          navigate(path);
          setPaletteOpen(false);
        }}
      />
    </>
  );
}

export default App;
