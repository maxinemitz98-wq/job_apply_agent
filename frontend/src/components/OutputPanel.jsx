import ReactMarkdown from 'react-markdown'

export default function OutputPanel({ title, markdown, downloadPath }) {
  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="font-semibold text-gray-800">{title}</h3>
        {downloadPath && (
          <a
            href={`/api/files/download?path=${encodeURIComponent(downloadPath)}`}
            className="text-sm text-blue-600 hover:underline"
            download
          >
            Download DOCX
          </a>
        )}
      </div>
      <div className="prose prose-sm max-w-none bg-white rounded-lg border border-gray-200 p-4 overflow-auto max-h-[60vh]">
        <ReactMarkdown>{markdown || '_No content yet._'}</ReactMarkdown>
      </div>
    </div>
  )
}
