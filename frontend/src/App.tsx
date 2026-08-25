import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { Layout } from './components/layout/Layout';
import MissionControl from './pages/MissionControl';
import Activity from './pages/Activity';
import Incidents from './pages/Incidents';
import Merchants from './pages/Merchants';

function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<MissionControl />} />
          <Route path="/activity" element={<Activity />} />
          <Route path="/incidents" element={<Incidents />} />
          <Route path="/merchants" element={<Merchants />} />
        </Routes>
      </Layout>
    </Router>
  );
}

export default App;
