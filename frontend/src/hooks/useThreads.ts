import { useCallback, useEffect, useState } from "react"
import { createThread, deleteThread, listThreads, updateThread } from "@/lib/api"
import type { Thread } from "@/types"

export function useThreads() {
  const [threads, setThreads] = useState<Thread[]>([])
  const [activeThreadId, setActiveThreadId] = useState<string | null>(null)

  const fetchThreads = useCallback(async () => {
    try {
      const data = await listThreads()
      setThreads(data)
    } catch (e) {
      console.error(e)
    }
  }, [])

  useEffect(() => {
    fetchThreads()
  }, [fetchThreads])

  const newThread = useCallback(async () => {
    const thread = await createThread()
    setThreads((prev) => [thread, ...prev])
    setActiveThreadId(thread.id)
    return thread
  }, [])

  const renameThread = useCallback(async (id: string, title: string) => {
    const updated = await updateThread(id, title)
    setThreads((prev) => prev.map((t) => (t.id === id ? updated : t)))
  }, [])

  const removeThread = useCallback(async (id: string) => {
    await deleteThread(id)
    setThreads((prev) => prev.filter((t) => t.id !== id))
    setActiveThreadId((prev) => (prev === id ? null : prev))
  }, [])

  return { threads, activeThreadId, setActiveThreadId, newThread, fetchThreads, renameThread, removeThread }
}
