import { useCallback } from "react"
import { ThreadList } from "@/components/ThreadList"
import { ChatWindow } from "@/components/ChatWindow"
import { MessageInput } from "@/components/MessageInput"
import { DocumentsPage } from "@/pages/DocumentsPage"
import { useThreads } from "@/hooks/useThreads"
import { useChat } from "@/hooks/useChat"

type Page = "chat" | "documents"

interface Props {
  activePage: Page
  onNavigate: (page: Page) => void
  userEmail: string
}

export function ChatPage({ activePage, onNavigate, userEmail }: Props) {
  const { threads, activeThreadId, setActiveThreadId, newThread, fetchThreads, renameThread, removeThread } = useThreads()

  const getOrCreateThread = useCallback(async () => {
    const thread = await newThread()
    return thread
  }, [newThread])

  const { messages, streamingContent, streaming, sourceCount, sendMessage, stopStreaming } = useChat(
    activeThreadId,
    getOrCreateThread,
    fetchThreads
  )

  return (
    <div className="flex h-screen">
      <div className="w-56 shrink-0">
        <ThreadList
          threads={threads}
          activeThreadId={activeThreadId}
          activePage={activePage}
          onNavigate={onNavigate}
          userEmail={userEmail}
          onSelect={setActiveThreadId}
          onNew={newThread}
          onRename={renameThread}
          onDelete={removeThread}
        />
      </div>

      <div className="flex flex-col flex-1 overflow-hidden bg-white">
        {activePage === "documents" ? (
          <DocumentsPage />
        ) : activeThreadId ? (
          <>
            <ChatWindow
              messages={messages}
              streamingContent={streamingContent}
              streaming={streaming}
              sourceCount={sourceCount}
            />
            <MessageInput
              onSend={sendMessage}
              disabled={streaming}
              streaming={streaming}
              onStop={stopStreaming}
            />
          </>
        ) : (
          <>
            <div className="flex-1 flex flex-col items-center justify-center gap-3 text-center px-4">
              <div className="w-12 h-12 rounded-full bg-gray-900 flex items-center justify-center">
                <svg xmlns="http://www.w3.org/2000/svg" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
              </div>
              <p className="text-sm text-gray-500">Select a chat or start a new one</p>
            </div>
            <MessageInput
              onSend={sendMessage}
              disabled={streaming}
              streaming={streaming}
              onStop={stopStreaming}
            />
          </>
        )}
      </div>
    </div>
  )
}
