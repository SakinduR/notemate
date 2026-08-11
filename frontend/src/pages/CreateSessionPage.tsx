import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { FileDropzone, MAX_SIZE_MB } from '../components/FileDropzone'
import { createSession, deleteSession } from '../api/sessions'
import { uploadDocuments } from '../api/documents'
import { ApiError } from '../api/client'

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function CreateSessionPage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [files, setFiles] = useState<File[]>([])
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  function addFiles(newFiles: File[]) {
    setError(null)
    const oversized = newFiles.find((f) => f.size > MAX_SIZE_MB * 1024 * 1024)
    if (oversized) {
      setError(`${oversized.name} exceeds the ${MAX_SIZE_MB}MB limit.`)
      return
    }
    const nonPdf = newFiles.find((f) => f.type !== 'application/pdf')
    if (nonPdf) {
      setError(`${nonPdf.name} isn't a PDF -- only PDF files are supported right now.`)
      return
    }
    setFiles((prev) => [...prev, ...newFiles])
  }

  function removeFile(index: number) {
    setFiles((prev) => prev.filter((_, i) => i !== index))
  }

  async function handleStart() {
    if (!name.trim()) {
      setError('Give this session a name first.')
      return
    }
    if (files.length === 0) {
      setError('Add at least one document to study.')
      return
    }

    setError(null)
    setSubmitting(true)

    let sessionId: string | null = null
    try {
      const session = await createSession(name.trim())
      sessionId = session.id
      await uploadDocuments(session.id, files)
      navigate(`/sessions/${session.id}`)
    } catch (err) {
      // Don't leave an empty orphaned session behind if the upload step failed.
      if (sessionId) await deleteSession(sessionId).catch(() => {})
      setError(err instanceof ApiError ? err.message : 'Something went wrong creating the session.')
      setSubmitting(false)
    }
  }

  return (
    <Layout>
      <Link to="/dashboard" className="mb-4 inline-block text-sm text-gray-500 hover:text-gray-700">
        ← Back to Dashboard
      </Link>
      <h1 className="mb-6 text-xl font-semibold text-gray-900">Create Study Session</h1>

      <div className="max-w-2xl space-y-6">
        <div>
          <label className="mb-1 block text-sm font-medium text-gray-700">Session Name</label>
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. Molecular Biology final review"
            className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500"
          />
        </div>

        <FileDropzone onFilesSelected={addFiles} />

        {files.length > 0 && (
          <div>
            <p className="mb-2 text-sm font-medium text-gray-700">Uploaded Files ({files.length})</p>
            <ul className="space-y-2">
              {files.map((file, i) => (
                <li
                  key={`${file.name}-${i}`}
                  className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm"
                >
                  <div>
                    <p className="font-medium text-gray-800">{file.name}</p>
                    <p className="text-xs text-gray-400">{formatSize(file.size)}</p>
                  </div>
                  <button onClick={() => removeFile(i)} className="text-gray-400 hover:text-rose-600">
                    Remove
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && <p className="text-sm text-rose-600">{error}</p>}

        <div className="flex justify-end gap-3">
          <Link to="/dashboard" className="rounded-lg px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100">
            Cancel
          </Link>
          <button
            onClick={handleStart}
            disabled={submitting}
            className="rounded-lg bg-brand-600 px-5 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
          >
            {submitting ? 'Starting session…' : 'Start Session'}
          </button>
        </div>
      </div>
    </Layout>
  )
}
