import { useRef, useState } from "react"
import { useDocuments } from "@/hooks/useDocuments"
import type { Document } from "@/types"

const STATUS_LABELS: Record<Document["status"], string> = {
  uploading: "Uploading...",
  parsing: "Parsing...",
  chunking: "Chunking...",
  embedding: "Embedding...",
  complete: "completed",
  error: "error",
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function DocumentsPage() {
  const { documents, uploading, error, uploadFile, removeDocument } = useDocuments()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [dragOver, setDragOver] = useState(false)

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (file) { uploadFile(file); e.target.value = "" }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files?.[0]
    if (file) uploadFile(file)
  }

  function handleDragOver(e: React.DragEvent) {
    e.preventDefault()
    setDragOver(true)
  }

  return (
    <div className="flex-1 overflow-auto bg-white px-8 py-8">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-xl font-semibold text-gray-900">Documents</h1>
          <p className="text-sm text-gray-500 mt-1">Upload documents to use as context in your chats.</p>
        </div>

        {error && (
          <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-600">
            {error}
          </div>
        )}

        {/* Drag-and-drop upload zone */}
        <div
          onClick={() => !uploading && fileInputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={() => setDragOver(false)}
          className={`mb-6 border-2 border-dashed rounded-xl py-10 flex flex-col items-center gap-2 transition-colors
            ${dragOver ? "border-gray-400 bg-gray-50" : "border-gray-300 hover:border-gray-400 hover:bg-gray-50"}
            ${uploading ? "opacity-60 cursor-not-allowed" : "cursor-pointer"}`}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="17 8 12 3 7 8" />
            <line x1="12" y1="3" x2="12" y2="15" />
          </svg>
          <p className="text-sm text-gray-600 font-medium">
            {uploading ? "Uploading..." : "Drop files here or click to upload"}
          </p>
          <p className="text-xs text-gray-400">Supported: .pdf (max 50 MB)</p>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept="application/pdf"
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Document list */}
        {documents.length > 0 && (
          <div className="space-y-2">
            {documents.map((doc) => (
              <DocumentRow key={doc.id} doc={doc} onDelete={() => removeDocument(doc.id)} />
            ))}
          </div>
        )}

        {documents.length === 0 && !uploading && (
          <p className="text-center text-sm text-gray-400 mt-4">No documents yet. Upload a PDF to get started.</p>
        )}
      </div>
    </div>
  )
}

function DocumentRow({ doc, onDelete }: { doc: Document; onDelete: () => void }) {
  const isProcessing = ["uploading", "parsing", "chunking", "embedding"].includes(doc.status)

  return (
    <div className="flex items-center gap-3 px-4 py-3 bg-white border border-gray-200 rounded-xl hover:border-gray-300 transition-colors">
      {/* File icon */}
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>

      {/* Filename */}
      <span className="flex-1 text-sm text-gray-800 truncate min-w-0">{doc.filename}</span>

      {/* Status badge */}
      <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium
        ${doc.status === "complete" ? "bg-green-100 text-green-700" :
          doc.status === "error" ? "bg-red-100 text-red-600" :
          "bg-gray-100 text-gray-500"}`}>
        {isProcessing
          ? <span className="animate-pulse">{STATUS_LABELS[doc.status]}</span>
          : STATUS_LABELS[doc.status]
        }
      </span>

      {/* Size · chunks */}
      {doc.status === "complete" && (
        <span className="shrink-0 text-xs text-gray-400">
          {formatBytes(doc.size_bytes)} · {doc.chunk_count} chunks
        </span>
      )}

      {/* Delete */}
      <button
        onClick={onDelete}
        disabled={isProcessing}
        className="shrink-0 text-sm text-gray-400 hover:text-red-500 disabled:opacity-30 transition-colors px-1"
      >
        Delete
      </button>
    </div>
  )
}
