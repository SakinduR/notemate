import type { ChatMessage } from '../api/types'

export function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === 'user'

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}>
      <div
        className={`max-w-[75%] rounded-2xl px-4 py-3 text-sm ${
          isUser ? 'bg-brand-600 text-white' : 'border border-gray-200 bg-white text-gray-800'
        }`}
      >
        <p className="whitespace-pre-wrap">{message.content}</p>

        {!isUser && message.citations && message.citations.length > 0 && (
          <div className="mt-3 border-t border-gray-100 pt-2">
            <p className="mb-1 text-xs font-medium text-gray-400">References & Citations</p>
            <div className="flex flex-wrap gap-1.5">
              {message.citations.map((c, i) => (
                <span
                  key={i}
                  className="rounded-md bg-brand-50 px-2 py-1 text-xs text-brand-700"
                  title={`${c.file_name}, page ${c.page}`}
                >
                  {c.file_name} · p.{c.page}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
