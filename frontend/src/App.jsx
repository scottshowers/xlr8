import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import { MessageSquare, Upload as UploadIcon, Activity, FileText, FolderKanban } from 'lucide-react';
import Chat from './components/Chat';
import Upload from './components/Upload';
import Status from './components/Status';
import Secure20Analysis from './pages/Secure20Analysis';
import Projects from './pages/Projects';

function App() {
  return (
    <Router>
      <div className="min-h-screen bg-gray-50">
        {/* Navigation */}
        <nav className="bg-white shadow-sm border-b border-gray-200">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <div className="flex justify-between h-16">
              <div className="flex">
                <div className="flex-shrink-0 flex items-center">
                  <h1 className="text-2xl font-bold text-blue-600">⚡ XLR8</h1>
                </div>
                <div className="hidden sm:ml-6 sm:flex sm:space-x-8">
                  <Link
                    to="/"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                  >
                    <MessageSquare className="mr-2" size={18} />
                    Chat
                  </Link>
                  <Link
                    to="/upload"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                  >
                    <UploadIcon className="mr-2" size={18} />
                    Upload
                  </Link>
                  <Link
                    to="/status"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                  >
                    <Activity className="mr-2" size={18} />
                    Status
                  </Link>
                  <Link
                    to="/projects"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                  >
                    <FolderKanban className="mr-2" size={18} />
                    Projects
                  </Link>
                  <Link
                    to="/secure2"
                    className="inline-flex items-center px-1 pt-1 text-sm font-medium text-gray-900 hover:text-blue-600"
                  >
                    <FileText className="mr-2" size={18} />
                    SECURE 2.0
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </nav>

        {/* Main Content */}
        <div className="py-10">
          <Routes>
            <Route path="/" element={<Chat />} />
            <Route path="/chat" element={<Chat />} />
            <Route path="/upload" element={<Upload />} />
            <Route path="/status" element={<Status />} />
            <Route path="/projects" element={<Projects />} />
            <Route path="/secure2" element={<Secure20Analysis />} />
          </Routes>
        </div>
      </div>
    </Router>
  );
}

export default App;
