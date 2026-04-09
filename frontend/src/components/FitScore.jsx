import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer } from 'recharts'

const LIKELIHOOD_COLORS = {
  LOW: 'text-red-600 bg-red-50',
  MEDIUM: 'text-yellow-600 bg-yellow-50',
  HIGH: 'text-blue-600 bg-blue-50',
  STRONG: 'text-green-600 bg-green-50',
}

export default function FitScore({ score }) {
  if (!score) return <p className="text-sm text-gray-400">No score available.</p>

  const radarData = (score.dimensions || []).map((d) => ({
    subject: d.name.split('&')[0].trim(),
    score: d.score,
    fullMark: 5,
  }))

  const likelihoodClass = LIKELIHOOD_COLORS[score.interview_likelihood] || 'text-gray-600 bg-gray-50'

  return (
    <div className="space-y-6">
      {/* Overall + likelihood */}
      <div className="flex items-center gap-6">
        <div className="text-center">
          <p className="text-4xl font-bold text-gray-900">{score.overall_score?.toFixed(1)}</p>
          <p className="text-xs text-gray-500">out of 10</p>
        </div>
        <div className={`px-4 py-2 rounded-lg font-semibold text-lg ${likelihoodClass}`}>
          {score.interview_likelihood}
        </div>
      </div>

      {/* Radar chart */}
      {radarData.length > 0 && (
        <div className="h-64">
          <ResponsiveContainer width="100%" height="100%">
            <RadarChart data={radarData}>
              <PolarGrid />
              <PolarAngleAxis dataKey="subject" tick={{ fontSize: 11 }} />
              <Radar name="Score" dataKey="score" stroke="#3b82f6" fill="#3b82f6" fillOpacity={0.3} />
            </RadarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Dimension breakdown */}
      <div className="space-y-2">
        {(score.dimensions || []).map((d) => (
          <div key={d.name} className="flex items-start gap-3">
            <div className="flex gap-0.5 mt-0.5">
              {[1, 2, 3, 4, 5].map((n) => (
                <div
                  key={n}
                  className={`w-3 h-3 rounded-sm ${n <= d.score ? 'bg-blue-500' : 'bg-gray-200'}`}
                />
              ))}
            </div>
            <div>
              <p className="text-sm font-medium text-gray-800">{d.name}</p>
              <p className="text-xs text-gray-500">{d.reason}</p>
            </div>
          </div>
        ))}
      </div>

      {/* Strengths + Gaps */}
      <div className="grid grid-cols-2 gap-4">
        <div>
          <h4 className="text-sm font-semibold text-green-700 mb-1">Strengths</h4>
          <ul className="space-y-1">
            {(score.strengths || []).map((s, i) => (
              <li key={i} className="text-xs text-gray-700 flex gap-1"><span>+</span>{s}</li>
            ))}
          </ul>
        </div>
        <div>
          <h4 className="text-sm font-semibold text-red-700 mb-1">Gaps to Address</h4>
          <ul className="space-y-1">
            {(score.gaps || []).map((g, i) => (
              <li key={i} className="text-xs text-gray-700 flex gap-1"><span>-</span>{g}</li>
            ))}
          </ul>
        </div>
      </div>
    </div>
  )
}
