import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listApplications } from '../api/client'

const STATUS_COLORS = {
  running: 'bg-yellow-100 text-yellow-800',
  ready: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
}

export default function ApplicationTracker({ refreshKey }) {
  const [apps, setApps] = useState([])
  const navigate = useNavigate()

  useEffect(() => {
    listApplications().then(({ data }) => setApps(data)).catch(() => {})
  }, [refreshKey])

  if (apps.length === 0) {
    return <p className="text-sm text-gray-400 mt-4">No applications yet.</p>
  }

  return (
    <div className="mt-4 space-y-2">
      <h3 className="text-sm font-semibold text-gray-600 uppercase tracking-wide">Past Applications</h3>
      {apps.map((a) => (
        <div
          key={a.id}
          className="flex items-center justify-between p-3 bg-white rounded-lg border border-gray-200 cursor-pointer hover:border-blue-400"
          onClick={() => navigate(`/application/${a.id}`)}
        >
          <div>
            <p className="font-medium text-sm text-gray-800">{a.role_title}</p>
            <p className="text-xs text-gray-500">{a.company_name}</p>
          </div>
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${STATUS_COLORS[a.status] || 'bg-gray-100 text-gray-600'}`}>
            {a.status.toUpperCase()}
          </span>
        </div>
      ))}
    </div>
  )
}
