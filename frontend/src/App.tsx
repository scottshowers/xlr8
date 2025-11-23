import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Secure20Analysis from './pages/Secure20Analysis';

export default function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<div className="p-8 text-white">XLR8 Home - Navigate to /secure20</div>} />
        <Route path="/secure20" element={<Secure20Analysis />} />
      </Routes>
    </Router>
  );
}
