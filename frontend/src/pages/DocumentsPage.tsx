import { useRef, useState } from "react"
import { useDocuments } from "@/hooks/useDocuments"
import type { Document } from "@/types"

const STATUS_LABELS: Record<Document["status"], string> = {
  uploading: "Uploading...",
  parsing: "Parsing...",
  extracting: "Extracting metadata...",
  chunking: "Chunking...",
  embedding: "Embedding...",
  complete: "Ready",
  error: "Error",
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return "—"
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function DocumentsPage() {
  const { documents, uploading, error, uploadFile, removeDocument, dedupResults } = useDocuments()
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
          <p className="text-xs text-gray-400">Supported: .pdf, .docx, .html, .md (max 50 MB)</p>
        </div>

        <input
          ref={fileInputRef}
          type="file"
          accept=".pdf,.docx,.html,.htm,.md,.markdown"
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Document list */}
        {documents.length > 0 && (
          <div className="space-y-2">
            {documents.map((doc) => (
              <DocumentRow key={doc.id} doc={doc} dedupResult={dedupResults[doc.id] ?? null} onDelete={() => removeDocument(doc.id)} />
            ))}
          </div>
        )}

        {documents.length === 0 && !uploading && (
          <p className="text-center text-sm text-gray-400 mt-4">No documents yet. Upload a document to get started.</p>
        )}
      </div>
    </div>
  )
}

function DocumentRow({ doc, dedupResult, onDelete }: { doc: Document; dedupResult: string | null; onDelete: () => void }) {
  const isProcessing = ["uploading", "parsing", "extracting", "chunking", "embedding"].includes(doc.status)

  function getBadge() {
    if (dedupResult === "already-up-to-date") {
      return { label: "Already up to date", style: "bg-green-100 text-green-700", animate: false }
    }
    if (dedupResult === "updated") {
      if (isProcessing) return { label: "Updating...", style: "bg-yellow-100 text-yellow-700", animate: true }
      if (doc.status === "complete") return { label: "Updated", style: "bg-green-100 text-green-700", animate: false }
    }
    if (doc.status === "complete") return { label: STATUS_LABELS.complete, style: "bg-green-100 text-green-700", animate: false }
    if (doc.status === "error") return { label: STATUS_LABELS.error, style: "bg-red-100 text-red-600", animate: false }
    return { label: STATUS_LABELS[doc.status], style: "bg-gray-100 text-gray-500", animate: true }
  }

  const badge = getBadge()

  return (
    <div className="flex items-start gap-3 px-4 py-3 bg-white border border-gray-200 rounded-xl hover:border-gray-300 transition-colors">
      {/* File icon */}
      <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#6b7280" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0 mt-0.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
        <polyline points="14 2 14 8 20 8" />
      </svg>

      {/* Filename + metadata pills */}
      <div className="flex-1 min-w-0 flex flex-col gap-1">
        <span className="text-sm text-gray-800 truncate">{doc.filename}</span>
        {doc.metadata && (
          <div className="flex flex-wrap gap-1">
            {(["document_type", "entity", "year", "quarter"] as const).map((key) =>
              doc.metadata![key] != null ? (
                <span key={key} className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600">
                  {String(doc.metadata![key])}
                </span>
              ) : null
            )}
          </div>
        )}
      </div>

      {/* Status badge */}
      <span className={`shrink-0 text-xs px-2 py-0.5 rounded-full font-medium ${badge.style}`}>
        {badge.animate ? <span className="animate-pulse">{badge.label}</span> : badge.label}
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
