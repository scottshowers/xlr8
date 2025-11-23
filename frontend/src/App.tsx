import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Secure20Analysis from './pages/Secure20Analysis';
import Dashboard from './pages/Dashboard';
import Projects from './pages/Projects';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/projects" element={<Projects />} />
        <Route path="/secure20" element={<Secure20Analysis />} />
      </Routes>
    </Router>
  );
}
