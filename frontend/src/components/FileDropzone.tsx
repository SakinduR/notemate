import { useRef, useState, type DragEvent } from 'react'

const MAX_SIZE_MB = 20

export function FileDropzone({ onFilesSelected }: { onFilesSelected: (files: File[]) => void }) {
  const [isDragging, setIsDragging] = useState(false)
  const inputRef = useRef<HTMLInputElement>(null)

  function handleFiles(fileList: FileList | null) {
    if (!fileList) return
    onFilesSelected(Array.from(fileList))
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault()
    setIsDragging(false)
    handleFiles(e.dataTransfer.files)
  }

  return (
    <div
      onClick={() => inputRef.current?.click()}
      onDragOver={(e) => {
        e.preventDefault()
        setIsDragging(true)
      }}
      onDragLeave={() => setIsDragging(false)}
      onDrop={handleDrop}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-xl border-2 border-dashed p-12 text-center transition ${
        isDragging ? 'border-brand-500 bg-brand-50' : 'border-gray-300 bg-gray-50 hover:border-brand-400'
      }`}
    >
      <div className="mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-brand-100 text-brand-600">↑</div>
      <p className="mb-1 font-medium text-gray-700">Drag and drop files to study</p>
      <p className="text-sm text-gray-400">Supports PDF · Max {MAX_SIZE_MB}MB each</p>
      <input
        ref={inputRef}
        type="file"
        accept="application/pdf"
        multiple
        className="hidden"
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  )
}

export { MAX_SIZE_MB }
