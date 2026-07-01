import { Routes, Route } from 'react-router-dom';
import { RecruiterDashboardPage } from './components/recruiter';

// The existing resume optimization flow lives at /resume — kept intact but
// hidden from challenge reviewers (they only see / which is the ranking system).
import ResumeFlow from './components/ResumeFlow';

function App() {
  return (
    <Routes>
      <Route path="/*" element={<RecruiterDashboardPage />} />
      <Route path="/resume/*" element={<ResumeFlow />} />
    </Routes>
  );
}

export default App;
