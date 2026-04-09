import { useEffect, useState } from 'react'

const AGENT_LABELS = {
  cv_tailor: 'CV Tailor',
  researcher: 'Researcher',
  letter_writer: 'Letter Writer',
  scorer: 'Scorer',
}

export default function StatusStream({ sessionId, onComplete }) {
  const [events, setEvents] = useState([])
  const [done, setDone] = useState(false)

  useEffect(() => {
    if (!sessionId) return

    const es = new EventSource(`/api/stream/${sessionId}`)

    const addEvent = (label, type) => {
      setEvents((prev) => [...prev, { label, type, ts: Date.now() }])
    }

    es.addEventListener('agent_started', (e) => {
      const { agent } = JSON.parse(e.data)
      addEvent(`${AGENT_LABELS[agent] || agent} started`, 'start')
    })

    es.addEventListener('agent_completed', (e) => {
      const { agent } = JSON.parse(e.data)
      addEvent(`${AGENT_LABELS[agent] || agent} complete`, 'complete')
    })

    es.addEventListener('pipeline_complete', () => {
      addEvent('Pipeline complete', 'done')
      setDone(true)
      es.close()
      onComplete?.()
    })

    es.addEventListener('pipeline_error', (e) => {
      const { error } = JSON.parse(e.data)
      addEvent(`Error: ${error}`, 'error')
      setDone(true)
      es.close()
    })

    es.addEventListener('done', () => {
      setDone(true)
      es.close()
      onComplete?.()
    })

    es.onerror = () => {
      if (!done) {
        addEvent('Connection lost', 'error')
        es.close()
      }
    }

    return () => es.close()
  }, [sessionId])

  if (!sessionId) return null

  return (
    <div className="bg-gray-900 rounded-lg p-4 text-sm font-mono">
      <p className="text-gray-400 mb-2 text-xs uppercase tracking-wide">Pipeline progress</p>
      <div className="space-y-1 max-h-40 overflow-y-auto">
        {events.map((ev, i) => (
          <div key={i} className={`flex items-center gap-2 ${
            ev.type === 'error' ? 'text-red-400' :
            ev.type === 'done' ? 'text-green-400' :
            ev.type === 'complete' ? 'text-blue-400' :
            'text-gray-300'
          }`}>
            <span>{ev.type === 'complete' ? '✓' : ev.type === 'error' ? '✗' : ev.type === 'done' ? '★' : '→'}</span>
            <span>{ev.label}</span>
          </div>
        ))}
        {!done && events.length > 0 && (
          <div className="text-yellow-400 animate-pulse">Running...</div>
        )}
      </div>
    </div>
  )
}
