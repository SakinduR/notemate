import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useParams } from 'react-router-dom'
import { Layout } from '../components/Layout'
import { ChatBubble } from '../components/ChatBubble'
import { SourceTypeBadge } from '../components/SourceTypeBadge'
import { getSession } from '../api/sessions'
import { getIngestStatus, listDocuments, uploadDocuments } from '../api/documents'
import { streamChat } from '../api/chat'
import type { ChatMessage, DocumentOut, StudySession } from '../api/types'

const POLL_INTERVAL_MS = 4000

export function ChatPage() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [session, setSession] = useState<StudySession | null>(null)
  const [documents, setDocuments] = useState<DocumentOut[]>([])
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [liveTrace, setLiveTrace] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  async function refresh() {
    if (!sessionId) return
    const [s, docs] = await Promise.all([getSession(sessionId), listDocuments(sessionId)])
    setSession(s)
    setDocuments(docs)
    return s
  }

  useEffect(() => {
    refresh().catch(() => setError('Could not load this session.'))
  }, [sessionId])

  // Poll ingestion status while documents are still being processed.
  useEffect(() => {
    if (!sessionId || !session) return
    if (session.ingestion_status !== 'ingesting') return

    const interval = setInterval(async () => {
      const status = await getIngestStatus(sessionId)
      if (status.status !== 'ingesting') {
        await refresh()
      }
    }, POLL_INTERVAL_MS)

    return () => clearInterval(interval)
  }, [sessionId, session?.ingestion_status])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, liveTrace])

  async function handleSend(e: FormEvent) {
    e.preventDefault()
    if (!sessionId || !input.trim() || sending) return

    const query = input.trim()
    setMessages((prev) => [...prev, { role: 'user', content: query }])
    setInput('')
    setSending(true)
    setLiveTrace([])

    await streamChat(sessionId, query, {
      onTrace: (_node, message) => setLiveTrace((prev) => [...prev, message]),
      onFinal: (answer, citations) => {
        setMessages((prev) => [...prev, { role: 'assistant', content: answer, citations }])
        setLiveTrace([])
        setSending(false)
      },
      onError: (message) => {
        setMessages((prev) => [...prev, { role: 'assistant', content: `Something went wrong: ${message}` }])
        setLiveTrace([])
        setSending(false)
      },
    })
  }

  async function handleAddMore(fileList: FileList | null) {
    if (!sessionId || !fileList || fileList.length === 0) return
    await uploadDocuments(sessionId, Array.from(fileList))
    await refresh()
  }

  function handleReset() {
    setMessages([])
  }

  function handleExport() {
    const lines = messages.map((m) => `**${m.role === 'user' ? 'You' : 'NoteMate'}:** ${m.content}`)
    const blob = new Blob([lines.join('\n\n')], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${session?.name ?? 'notemate-chat'}.md`
    a.click()
    URL.revokeObjectURL(url)
  }

  if (error) {
    return (
      <Layout>
        <p className="text-rose-600">{error}</p>
      </Layout>
    )
  }

  if (!session) {
    return (
      <Layout>
        <p className="text-gray-400">Loading…</p>
      </Layout>
    )
  }

  const isReady = session.ingestion_status === 'ready'
  const isFailed = session.ingestion_status === 'failed'

  return (
    <Layout>
      <Link to="/dashboard" className="mb-4 inline-block text-sm text-gray-500 hover:text-gray-700">
        ← Back to Dashboard
      </Link>

      <div className="flex gap-6" style={{ height: 'calc(100vh - 220px)' }}>
        <aside className="flex w-72 shrink-0 flex-col rounded-xl border border-gray-200 bg-white p-4">
          <h2 className="mb-3 text-sm font-semibold text-gray-700">Session Materials</h2>
          <ul className="flex-1 space-y-2 overflow-y-auto">
            {documents.map((doc) => (
              <li key={doc.id} className="rounded-lg border border-gray-100 p-2">
                <p className="truncate text-sm text-gray-800" title={doc.file_name}>
                  {doc.file_name}
                </p>
                <div className="mt-1">
                  <SourceTypeBadge sourceType={doc.source_type} />
                </div>
              </li>
            ))}
            {documents.length === 0 && <li className="text-sm text-gray-400">No documents yet.</li>}
          </ul>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="mt-3 rounded-lg border border-dashed border-gray-300 py-2 text-sm text-gray-500 hover:border-brand-400 hover:text-brand-600"
          >
            + Add More
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept="application/pdf"
            multiple
            className="hidden"
            onChange={(e) => handleAddMore(e.target.files)}
          />
        </aside>

        <section className="flex flex-1 flex-col rounded-xl border border-gray-200 bg-white">
          <div className="flex items-center justify-between border-b border-gray-100 px-5 py-3">
            <h1 className="font-semibold text-gray-900">{session.name}</h1>
            <div className="flex gap-2">
              <button onClick={handleReset} className="text-sm text-gray-500 hover:text-gray-700">
                Reset Chat
              </button>
              <button onClick={handleExport} disabled={messages.length === 0} className="text-sm text-gray-500 hover:text-gray-700 disabled:opacity-40">
                Export Notes
              </button>
            </div>
          </div>

          <div ref={scrollRef} className="flex-1 space-y-4 overflow-y-auto p-5">
            {!isReady && !isFailed && (
              <div className="rounded-lg bg-amber-50 px-4 py-3 text-sm text-amber-700">
                Processing your documents… this page will update automatically once they're ready.
              </div>
            )}
            {isFailed && (
              <div className="rounded-lg bg-rose-50 px-4 py-3 text-sm text-rose-700">
                Ingestion failed{session ? '' : ''}. Try adding your documents again.
              </div>
            )}
            {isReady && messages.length === 0 && (
              <p className="text-sm text-gray-400">Ask a question about your uploaded materials to get started.</p>
            )}

            {messages.map((m, i) => (
              <ChatBubble key={i} message={m} />
            ))}

            {sending && (
              <div className="flex justify-start">
                <div className="max-w-[75%] rounded-2xl border border-gray-200 bg-white px-4 py-3 text-xs text-gray-500">
                  {liveTrace.length === 0 ? 'Thinking…' : liveTrace[liveTrace.length - 1]}
                </div>
              </div>
            )}
          </div>

          <form onSubmit={handleSend} className="flex gap-2 border-t border-gray-100 p-4">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              disabled={!isReady || sending}
              placeholder={isReady ? `Ask a question about "${session.name}"…` : 'Waiting for documents to finish processing…'}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm outline-none focus:border-brand-500 focus:ring-1 focus:ring-brand-500 disabled:bg-gray-50"
            />
            <button
              type="submit"
              disabled={!isReady || sending || !input.trim()}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-40"
            >
              Send
            </button>
          </form>
        </section>
      </div>
    </Layout>
  )
}
