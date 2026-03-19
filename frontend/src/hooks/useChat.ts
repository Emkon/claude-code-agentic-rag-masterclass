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
            const updated = await listMessages(tid!)
            setMessages(updated)
            onThreadsChanged?.()
          },
          (count) => setSourceCount(count),
          controller.signal
        )
      } catch (e: any) {
        if (e.name !== "AbortError") console.error(e)
        setStreaming(false)
        setStreamingContent("")
      }
    },
    [threadId, streaming, getOrCreateThread, onThreadsChanged]
  )

  return { messages, streamingContent, streaming, sourceCount, sendMessage, stopStreaming }
}
