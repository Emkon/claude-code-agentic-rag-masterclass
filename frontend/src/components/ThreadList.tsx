import { useState } from "react"
import { supabase } from "@/lib/supabaseClient"
import { ScrollArea } from "@/components/ui/scroll-area"
import { cn } from "@/lib/utils"
import type { Thread } from "@/types"

type Page = "chat" | "documents"

interface Props {
  threads: Thread[]
  activeThreadId: string | null
  activePage: Page
  onNavigate: (page: Page) => void
  userEmail: string
  onSelect: (id: string) => void
  onNew: () => void
  onRename: (id: string, title: string) => void
  onDelete: (id: string) => void
}

function getInitials(email: string): string {
  const name = email.split("@")[0]
  const parts = name.split(/[._-]/)
  return parts
    .slice(0, 2)
    .map((p) => p[0]?.toUpperCase() ?? "")
    .join("") || (email[0]?.toUpperCase() ?? "?")
}

export function ThreadList({
  threads, activeThreadId, activePage, onNavigate, userEmail,
  onSelect, onNew, onRename, onDelete,
}: Props) {
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editValue, setEditValue] = useState("")

  function startEdit(t: Thread, e: React.MouseEvent) {
    e.stopPropagation()
    setEditingId(t.id)
    setEditValue(t.title)
  }

  function commitEdit(id: string) {
    const trimmed = editValue.trim()
    if (trimmed) onRename(id, trimmed)
    setEditingId(null)
  }

  const initials = getInitials(userEmail)

  return (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      {/* Brand */}
      <div className="px-4 py-4 border-b border-gray-100">
        <span className="text-sm font-bold text-gray-900">RAG Chat</span>
      </div>

      {/* Nav */}
      <nav className="px-2 py-2 space-y-0.5">
        <button
          onClick={() => onNavigate("chat")}
          className={cn(
            "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors text-left",
            activePage === "chat"
              ? "bg-gray-100 text-gray-900 font-medium"
              : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
          )}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
          </svg>
          Chat
        </button>

        <button
          onClick={() => onNavigate("documents")}
          className={cn(
            "w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm transition-colors text-left",
            activePage === "documents"
              ? "bg-gray-100 text-gray-900 font-medium"
              : "text-gray-600 hover:bg-gray-50 hover:text-gray-900"
          )}
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
            <polyline points="14 2 14 8 20 8" />
          </svg>
          Documents
        </button>
      </nav>

      {/* Thread list — only on chat page */}
      {activePage === "chat" && (
        <>
          <div className="px-4 pt-3 pb-1 flex items-center justify-between">
            <span className="text-xs font-medium text-gray-400 uppercase tracking-wider">Chats</span>
            <button
              onClick={onNew}
              className="text-gray-400 hover:text-gray-600 transition-colors"
              title="New chat"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>
          </div>

          <ScrollArea className="flex-1 px-2">
            <div className="space-y-0.5 py-1 pb-2">
              {threads.length === 0 && (
                <p className="text-xs text-gray-400 px-3 py-2">No chats yet</p>
              )}
              {threads.map((t) => (
                <div
                  key={t.id}
                  className={cn(
                    "group relative flex items-center rounded-lg transition-colors",
                    activeThreadId === t.id ? "bg-gray-100" : "hover:bg-gray-50"
                  )}
                >
                  {editingId === t.id ? (
                    <input
                      autoFocus
                      className="flex-1 text-xs px-3 py-2 bg-white border border-gray-300 rounded-lg outline-none text-gray-900"
                      value={editValue}
                      onChange={(e) => setEditValue(e.target.value)}
                      onBlur={() => commitEdit(t.id)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter") commitEdit(t.id)
                        if (e.key === "Escape") setEditingId(null)
                      }}
                    />
                  ) : (
                    <>
                      <button
                        className="flex-1 text-left px-3 py-2 min-w-0"
                        onClick={() => onSelect(t.id)}
                      >
                        <span className="text-xs text-gray-700 truncate block">{t.title}</span>
                      </button>
                      <div className="hidden group-hover:flex items-center gap-0.5 pr-2 shrink-0">
                        <button
                          className="p-1 text-gray-400 hover:text-gray-600"
                          onClick={(e) => startEdit(t, e)}
                          title="Rename"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
                          </svg>
                        </button>
                        <button
                          className="p-1 text-gray-400 hover:text-red-400"
                          onClick={(e) => { e.stopPropagation(); onDelete(t.id) }}
                          title="Delete"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                            <polyline points="3 6 5 6 21 6" />
                            <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                            <path d="M10 11v6M14 11v6" />
                            <path d="M9 6V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2" />
                          </svg>
                        </button>
                      </div>
                    </>
                  )}
                </div>
              ))}
            </div>
          </ScrollArea>
        </>
      )}

      {activePage === "documents" && <div className="flex-1" />}

      {/* User profile */}
      <div className="px-3 py-3 border-t border-gray-100 flex items-center gap-2.5">
        <div className="w-7 h-7 rounded-full bg-gray-900 text-white flex items-center justify-center text-xs font-semibold shrink-0">
          {initials}
        </div>
        <p className="flex-1 text-xs text-gray-600 truncate min-w-0">{userEmail}</p>
        <button
          onClick={() => supabase.auth.signOut()}
          className="shrink-0 text-gray-400 hover:text-gray-600 transition-colors"
          title="Sign out"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
            <polyline points="16 17 21 12 16 7" />
            <line x1="21" y1="12" x2="9" y2="12" />
          </svg>
        </button>
      </div>
    </div>
  )
}
