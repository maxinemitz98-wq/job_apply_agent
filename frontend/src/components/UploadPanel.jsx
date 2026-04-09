import { useState, useRef } from 'react'
import { uploadCV, startApplication } from '../api/client'

export default function UploadPanel({ onApplicationStarted }) {
  const [cvFile, setCvFile] = useState(null)
  const [cvFileId, setCvFileId] = useState(null)
  const [jdText, setJdText] = useState('')
  const [companyName, setCompanyName] = useState('')
  const [roleTitle, setRoleTitle] = useState('')
  const [userNotes, setUserNotes] = useState('')
  const [uploading, setUploading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const fileRef = useRef()

  const handleFileChange = async (e) => {
    const file = e.target.files[0]
    if (!file) return
    setCvFile(file)
    setError(null)
    setUploading(true)
    try {
      const { data } = await uploadCV(file)
      setCvFileId(data.cv_file_id)
    } catch (err) {
      setError(err.response?.data?.detail || 'Upload failed.')
    } finally {
      setUploading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!cvFileId) { setError('Upload a CV first.'); return }
    if (!jdText.trim()) { setError('Paste a job description.'); return }
    if (!companyName.trim()) { setError('Enter a company name.'); return }
    if (!roleTitle.trim()) { setError('Enter a role title.'); return }

    setSubmitting(true)
    setError(null)
    try {
      const { data } = await startApplication({
        jd_text: jdText,
        company_name: companyName,
        role_title: roleTitle,
        cv_file_id: cvFileId,
        user_notes: userNotes || null,
      })
      onApplicationStarted(data)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to start pipeline.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <h2 className="text-lg font-semibold text-gray-800">New Application</h2>

      {/* CV Upload */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">CV (PDF or DOCX)</label>
        <div
          className="border-2 border-dashed border-gray-300 rounded-lg p-4 text-center cursor-pointer hover:border-blue-400"
          onClick={() => fileRef.current.click()}
        >
          {uploading ? (
            <span className="text-sm text-gray-500">Uploading...</span>
          ) : cvFileId ? (
            <span className="text-sm text-green-600">{cvFile?.name} — uploaded</span>
          ) : (
            <span className="text-sm text-gray-500">Click to upload or drag & drop</span>
          )}
        </div>
        <input ref={fileRef} type="file" accept=".pdf,.docx,.doc" onChange={handleFileChange} className="hidden" />
      </div>

      {/* Company + Role */}
      <div className="grid grid-cols-2 gap-3">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Company</label>
          <input
            type="text"
            value={companyName}
            onChange={(e) => setCompanyName(e.target.value)}
            placeholder="e.g. Anthropic"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">Role</label>
          <input
            type="text"
            value={roleTitle}
            onChange={(e) => setRoleTitle(e.target.value)}
            placeholder="e.g. Software Engineer"
            className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
          />
        </div>
      </div>

      {/* JD */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Job Description</label>
        <textarea
          value={jdText}
          onChange={(e) => setJdText(e.target.value)}
          rows={8}
          placeholder="Paste the full job description here..."
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400 resize-y"
        />
      </div>

      {/* Notes */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-1">Notes (optional)</label>
        <input
          type="text"
          value={userNotes}
          onChange={(e) => setUserNotes(e.target.value)}
          placeholder="e.g. Emphasise German language skills"
          className="w-full border border-gray-300 rounded px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-400"
        />
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}

      <button
        type="submit"
        disabled={submitting || uploading}
        className="w-full bg-blue-600 text-white py-2 rounded font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {submitting ? 'Running pipeline...' : 'Run Agent'}
      </button>
    </form>
  )
}
