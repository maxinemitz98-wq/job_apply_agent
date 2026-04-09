import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { getApplication } from '../api/client'
import OutputPanel from '../components/OutputPanel'
import FitScore from '../components/FitScore'

const TABS = ['Tailored CV', 'Company Brief', 'Motivation Letter', 'Fit Score']

export default function ApplicationDetail() {
  const { id } = useParams()
  const [app, setApp] = useState(null)
  const [loading, setLoading] = useState(true)
  const [tab, setTab] = useState(0)

  useEffect(() => {
    getApplication(id)
      .then(({ data }) => setApp(data))
      .finally(() => setLoading(false))
  }, [id])

  if (loading) {
    return <div className="max-w-4xl mx-auto px-4 py-8 text-gray-500">Loading...</div>
  }

  if (!app) {
    return <div className="max-w-4xl mx-auto px-4 py-8 text-red-600">Application not found.</div>
  }

  const outputs = app.outputs || {}

  return (
    <div className="max-w-4xl mx-auto px-4 py-8">
      {/* Back */}
      <Link to="/" className="text-sm text-blue-600 hover:underline mb-4 inline-block">
        &larr; Dashboard
      </Link>

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-bold text-gray-900">{app.role_title}</h1>
          <p className="text-gray-500">{app.company_name}</p>
        </div>
        <span className={`text-sm px-3 py-1 rounded-full font-medium ${
          app.status === 'ready' ? 'bg-green-100 text-green-800' :
          app.status === 'running' ? 'bg-yellow-100 text-yellow-800' :
          'bg-red-100 text-red-800'
        }`}>
          {app.status.toUpperCase()}
        </span>
      </div>

      {app.status === 'failed' && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 text-sm text-red-700">
          Pipeline failed: {app.error}
        </div>
      )}

      {app.status === 'running' && (
        <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6 text-sm text-yellow-700">
          Pipeline is still running. Refresh to check for results.
        </div>
      )}

      {/* Tabs */}
      {app.status === 'ready' && (
        <div>
          <div className="flex border-b border-gray-200 mb-6">
            {TABS.map((t, i) => (
              <button
                key={t}
                onClick={() => setTab(i)}
                className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                  tab === i
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {t}
              </button>
            ))}
          </div>

          {tab === 0 && (
            <OutputPanel
              title="Tailored CV"
              markdown={outputs.tailored_cv_md}
              downloadPath={outputs.tailored_cv_path}
            />
          )}
          {tab === 1 && (
            <OutputPanel
              title="Company Research Brief"
              markdown={outputs.research_brief_md}
            />
          )}
          {tab === 2 && (
            <OutputPanel
              title="Motivation Letter"
              markdown={outputs.letter_md}
              downloadPath={outputs.letter_path}
            />
          )}
          {tab === 3 && (
            <div>
              <h3 className="font-semibold text-gray-800 mb-4">Fit Score</h3>
              <FitScore score={outputs.score} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
