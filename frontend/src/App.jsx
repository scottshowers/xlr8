import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { MessageSquare, Upload as UploadIcon, Activity, FolderKanban, FileText } from 'lucide-react';
import axios from 'axios';

// Components
import Chat from './components/Chat';
import Upload from './components/Upload';
import Status from './components/Status';

// Pages
import Projects from './pages/Projects';
import Secure20Analysis from './pages/Secure20Analysis';

const API_URL = import.meta.env.VITE_API_URL || 'https://hcmpact-xlr8-production.up.railway.app';

function App() {
  const [projects, setProjects] = useState([]);

  // Refresh projects function that can be called from child components
  const refreshProjects = async () => {
    try {
      const response = await axios.get(`${API_URL}/api/projects/list`);
      setProjects(response.data);
    } catch (error) {
      console.error('Failed to load projects:', error);
    }
  };

  // Load projects on mount
  useEffect(() => {
    refreshProjects();
  }, []);

  // Define functional areas for components
  const functionalAreas = [
    'Payroll',
    'Benefits', 
    'Time & Attendance',
    'Recruiting',
    'Onboarding',
    'Performance',
    'Compensation',
    'Learning',
    'Analytics'
  ];

  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex space-x-8">
                <Link
                  to="/chat"
                  className="inline-flex items-center px-4 py-2 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                >
                  <MessageSquare className="mr-2 h-5 w-5" />
                  Chat
                </Link>
                <Link
                  to="/upload"
                  className="inline-flex items-center px-4 py-2 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                >
                  <UploadIcon className="mr-2 h-5 w-5" />
                  Upload
                </Link>
                <Link
                  to="/status"
                  className="inline-flex items-center px-4 py-2 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                >
                  <Activity className="mr-2 h-5 w-5" />
                  Status
                </Link>
                <Link
                  to="/projects"
                  className="inline-flex items-center px-4 py-2 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                >
                  <FolderKanban className="mr-2 h-5 w-5" />
                  Projects
                </Link>
                <Link
                  to="/secure20"
                  className="inline-flex items-center px-4 py-2 border-b-2 border-transparent text-sm font-medium text-gray-500 hover:text-gray-700 hover:border-gray-300"
                >
                  <FileText className="mr-2 h-5 w-5" />
                  SECURE 2.0 Analysis
                </Link>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
          <Routes>
            <Route path="/" element={<Chat projects={projects} functionalAreas={functionalAreas} />} />
            <Route path="/chat" element={<Chat projects={projects} functionalAreas={functionalAreas} />} />
            <Route 
              path="/upload" 
              element={
                <Upload 
                  projects={projects} 
                  functionalAreas={functionalAreas}
                  onProjectCreated={refreshProjects}
                />
              } 
            />
            <Route path="/status" element={<Status projects={projects} />} />
            <Route path="/projects" element={<Projects onProjectsChanged={refreshProjects} />} />
            <Route path="/secure20" element={<Secure20Analysis />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
