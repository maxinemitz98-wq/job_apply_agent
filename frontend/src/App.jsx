import { Routes, Route } from 'react-router-dom'
import Dashboard from './pages/Dashboard'
import ApplicationDetail from './pages/ApplicationDetail'

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/application/:id" element={<ApplicationDetail />} />
      </Routes>
    </div>
  )
}
