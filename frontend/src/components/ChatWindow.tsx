import { useEffect, useRef } from "react"
import { ScrollArea } from "@/components/ui/scroll-area"
import type { Message } from "@/types"

interface Props {
  messages: Message[]
  streamingContent: string
  streaming: boolean
  sourceCount?: number
  activeToolName?: string | null
  subagentRunning?: boolean
  subagentTools?: string[]
}

export function ChatWindow({
  messages,
  streamingContent,
  streaming,
  sourceCount = 0,
  activeToolName = null,
  subagentRunning = false,
  subagentTools = [],
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages, streamingContent])

  return (
    <ScrollArea className="flex-1 bg-white">
      <div className="py-6 px-4 max-w-3xl mx-auto space-y-6">
        {messages.map((msg) => (
          <MessageRow key={msg.id} role={msg.role} content={msg.content} />
        ))}
        {streaming && !streamingContent && (
          <ActivityIndicator
            sourceCount={sourceCount}
            activeToolName={activeToolName}
            subagentRunning={subagentRunning}
            subagentTools={subagentTools}
          />
        )}
        {streaming && streamingContent && (
          <MessageRow role="assistant" content={streamingContent} streaming />
        )}
        <div ref={bottomRef} />
      </div>
    </ScrollArea>
  )
}

function ActivityIndicator({
  sourceCount,
  activeToolName,
  subagentRunning,
  subagentTools,
}: {
  sourceCount: number
  activeToolName: string | null
  subagentRunning: boolean
  subagentTools: string[]
}) {
  const botAvatar = (
    <div className="shrink-0 w-7 h-7 rounded-full bg-gray-900 flex items-center justify-center mt-0.5">
      <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>
    </div>
  )

  if (subagentRunning) {
    return (
      <div className="flex items-start gap-3">
        {botAvatar}
        <div className="space-y-1">
          <p className="text-xs text-gray-500 animate-pulse">Sub-agent analyzing...</p>
          {subagentTools.map((t, i) => (
            <p key={i} className="text-xs text-gray-400 pl-3">↳ {t.replace(/_/g, " ")}</p>
          ))}
        </div>
      </div>
    )
  }

  if (activeToolName) {
    return (
      <div className="flex items-start gap-3">
        {botAvatar}
        <p className="text-xs text-gray-400 mt-2 animate-pulse">
          Running {activeToolName.replace(/_/g, " ")}...
        </p>
      </div>
    )
  }

  if (sourceCount > 0) {
    return (
      <div className="flex items-start gap-3">
        {botAvatar}
        <p className="text-xs text-gray-400 mt-2 animate-pulse">
          Searching {sourceCount} document chunk{sourceCount !== 1 ? "s" : ""}...
        </p>
      </div>
    )
  }

  return null
}

function MessageRow({
  role,
  content,
  streaming,
}: {
  role: string
  content: string
  streaming?: boolean
}) {
  const isUser = role === "user"

  if (isUser) {
    return (
      <div className="flex justify-end">
        <div className="max-w-[75%] bg-gray-900 text-white rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm whitespace-pre-wrap">
          {content}
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-3">
      <div className="shrink-0 w-7 h-7 rounded-full bg-gray-900 flex items-center justify-center mt-0.5">
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>
      </div>
      <div className="max-w-[75%] bg-gray-100 text-gray-900 rounded-2xl rounded-tl-sm px-4 py-2.5 text-sm whitespace-pre-wrap">
        {content}
        {streaming && <span className="ml-1 opacity-50">▋</span>}
      </div>
    </div>
  )
}
