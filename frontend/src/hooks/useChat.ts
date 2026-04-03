import { useCallback, useEffect, useRef, useState } from "react"
import { listMessages, sendMessageStream } from "@/lib/api"
import type { Message } from "@/types"

export function useChat(
  threadId: string | null,
  getOrCreateThread: () => Promise<{ id: string }>,
  onThreadsChanged?: () => void
) {
  const [messages, setMessages] = useState<Message[]>([])
  const [streamingContent, setStreamingContent] = useState("")
  const [streaming, setStreaming] = useState(false)
  const [sourceCount, setSourceCount] = useState(0)
  const [activeToolName, setActiveToolName] = useState<string | null>(null)
  const [subagentRunning, setSubagentRunning] = useState(false)
  const [subagentTools, setSubagentTools] = useState<string[]>([])
  const activeThreadRef = useRef<string | null>(null)
  const abortRef = useRef<AbortController | null>(null)

  useEffect(() => {
    if (!threadId) {
      setMessages([])
      return
    }
    activeThreadRef.current = threadId
    listMessages(threadId).then(setMessages).catch(console.error)
  }, [threadId])

  const stopStreaming = useCallback(() => {
    abortRef.current?.abort()
  }, [])

  const sendMessage = useCallback(
    async (content: string) => {
      if (streaming) return

      let tid = threadId
      if (!tid) {
        const thread = await getOrCreateThread()
        tid = thread.id
      }

      setStreaming(true)
      setStreamingContent("")
      setSourceCount(0)
      setActiveToolName(null)
      setSubagentRunning(false)
      setSubagentTools([])

      const controller = new AbortController()
      abortRef.current = controller

      try {
        await sendMessageStream(
          tid,
          content,
          (token) => setStreamingContent((prev) => prev + token),
          async () => {
            setStreaming(false)
            setStreamingContent("")
            setActiveToolName(null)
            setSubagentRunning(false)
            setSubagentTools([])
            const updated = await listMessages(tid!)
            setMessages(updated)
            onThreadsChanged?.()
          },
          (count) => setSourceCount(count),
          controller.signal,
          (name) => setActiveToolName(name),
          () => { setSubagentRunning(true); setSubagentTools([]) },
          (name) => setSubagentTools((prev) => [...prev, name]),
          () => setSubagentRunning(false),
        )
      } catch (e: any) {
        if (e.name !== "AbortError") console.error(e)
        setStreaming(false)
        setStreamingContent("")
        setActiveToolName(null)
        setSubagentRunning(false)
        setSubagentTools([])
      }
    },
    [threadId, streaming, getOrCreateThread, onThreadsChanged]
  )

  return { messages, streamingContent, streaming, sourceCount, activeToolName, subagentRunning, subagentTools, sendMessage, stopStreaming }
}
