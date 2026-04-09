import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import UploadPanel from '../components/UploadPanel'
import ApplicationTracker from '../components/ApplicationTracker'
import StatusStream from '../components/StatusStream'

export default function Dashboard() {
  const [activeSession, setActiveSession] = useState(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const navigate = useNavigate()

  const handleApplicationStarted = (data) => {
    setActiveSession(data)
  }

  const handlePipelineComplete = () => {
    setRefreshKey((k) => k + 1)
    if (activeSession?.application_id) {
      navigate(`/application/${activeSession.application_id}`)
    }
  }

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-bold text-gray-900 mb-8">Job Application Agent</h1>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Left: upload + submit */}
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
            <UploadPanel onApplicationStarted={handleApplicationStarted} />
          </div>

          {activeSession && (
            <StatusStream
              sessionId={activeSession.session_id}
              onComplete={handlePipelineComplete}
            />
          )}
        </div>

        {/* Right: past applications */}
        <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-gray-800 mb-2">Applications</h2>
          <ApplicationTracker refreshKey={refreshKey} />
        </div>
      </div>
    </div>
  )
}
