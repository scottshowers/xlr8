import { BrowserRouter, Routes, Route, Link } from 'react-router-dom'
import { useState, useEffect } from 'react'
import Chat from './components/Chat'
import Upload from './components/Upload'
import Status from './components/Status'
import Secure20Analysis from './pages/Secure20Analysis'
import api from './services/api'

function App() {
  const [projects, setProjects] = useState([])
  const [functionalAreas, setFunctionalAreas] = useState([])
  const [health, setHealth] = useState(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      const [projectsRes, areasRes, healthRes] = await Promise.all([
        api.get('/projects'),
        api.get('/functional-areas'),
        api.get('/health')
      ])
      setProjects(projectsRes.data.projects || [])
      setFunctionalAreas(areasRes.data.functional_areas || [])
      setHealth(healthRes.data)
    } catch (err) {
      console.error('Error loading data:', err)
    }
  }

  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-100">
        <nav className="bg-blue-600 text-white p-4">
          <div className="container mx-auto flex items-center justify-between">
            <h1 className="text-2xl font-bold">XLR8</h1>
            <div className="flex gap-4">
              <Link to="/" className="hover:underline">Chat</Link>
              <Link to="/upload" className="hover:underline">Upload</Link>
              <Link to="/status" className="hover:underline">Status</Link>
              <Link to="/secure20" className="hover:underline">SECURE 2.0</Link>
            </div>
            {health && (
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${health.status === 'healthy' ? 'bg-green-400' : 'bg-red-400'}`}></div>
                <span className="text-sm">{health.status}</span>
              </div>
            )}
          </div>
        </nav>
        
        <div className="container mx-auto p-4">
          <Routes>
            <Route path="/" element={<Chat projects={projects} functionalAreas={functionalAreas} />} />
            <Route path="/upload" element={<Upload projects={projects} functionalAreas={functionalAreas} />} />
            <Route path="/status" element={<Status />} />
            <Route path="/secure20" element={<Secure20Analysis />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}

export default App
