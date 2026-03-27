import { useCallback, useEffect, useState } from "react"
import { supabase } from "@/lib/supabaseClient"
import { listDocuments, uploadDocument, deleteDocument } from "@/lib/api"
import type { Document } from "@/types"

export function useDocuments() {
  const [documents, setDocuments] = useState<Document[]>([])
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [dedupResults, setDedupResults] = useState<Record<string, string>>({})

  const fetchDocuments = useCallback(async () => {
    try {
      const data = await listDocuments()
      setDocuments(data)
    } catch (e) {
      console.error(e)
    }
  }, [])

  useEffect(() => {
    fetchDocuments()
  }, [fetchDocuments])

  // Realtime: listen for status updates on the documents table
  useEffect(() => {
    const channel = supabase
      .channel("documents-status")
      .on(
        "postgres_changes",
        { event: "UPDATE", schema: "public", table: "documents" },
        (payload) => {
          setDocuments((prev) =>
            prev.map((doc) =>
              doc.id === payload.new.id ? (payload.new as Document) : doc
            )
          )
        }
      )
      .subscribe()

    return () => {
      supabase.removeChannel(channel)
    }
  }, [])

  const uploadFile = useCallback(async (file: File): Promise<Document | null> => {
    setUploading(true)
    setError(null)
    try {
      const { doc, dedupResult } = await uploadDocument(file)
      // Upsert: update in place if same id already exists (re-upload case), otherwise prepend
      setDocuments((prev) => {
        const exists = prev.some((d) => d.id === doc.id)
        return exists ? prev.map((d) => d.id === doc.id ? doc : d) : [doc, ...prev]
      })
      if (dedupResult) {
        setDedupResults((prev) => ({ ...prev, [doc.id]: dedupResult }))
      }
      return doc
    } catch (e: any) {
      setError(e.message || "Upload failed")
      return null
    } finally {
      setUploading(false)
    }
  }, [])

  const removeDocument = useCallback(async (documentId: string) => {
    try {
      await deleteDocument(documentId)
      setDocuments((prev) => prev.filter((d) => d.id !== documentId))
    } catch (e) {
      console.error(e)
    }
  }, [])

  return { documents, uploading, error, uploadFile, removeDocument, dedupResults }
}
