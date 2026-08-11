const LABELS: Record<string, string> = {
  lecture_slides: 'Lecture Slides',
  reference_book: 'Reference Book',
  past_paper: 'Past Paper',
  general_notes: 'Notes',
}

const COLORS: Record<string, string> = {
  lecture_slides: 'bg-blue-100 text-blue-700',
  reference_book: 'bg-emerald-100 text-emerald-700',
  past_paper: 'bg-rose-100 text-rose-700',
  general_notes: 'bg-amber-100 text-amber-700',
}

export function SourceTypeBadge({ sourceType }: { sourceType: string | null }) {
  if (!sourceType) {
    return <span className="rounded-full bg-gray-100 px-2.5 py-0.5 text-xs font-medium text-gray-500">Processing…</span>
  }
  const label = LABELS[sourceType] ?? sourceType
  const color = COLORS[sourceType] ?? 'bg-gray-100 text-gray-700'
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${color}`}>{label}</span>
}
