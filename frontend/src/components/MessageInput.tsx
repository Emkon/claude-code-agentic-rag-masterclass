import { useState } from "react"

interface Props {
  onSend: (content: string) => void
  disabled?: boolean
  streaming?: boolean
  onStop?: () => void
}

export function MessageInput({ onSend, disabled, streaming, onStop }: Props) {
  const [value, setValue] = useState("")

  function handleSend() {
    const trimmed = value.trim()
    if (!trimmed || disabled) return
    onSend(trimmed)
    setValue("")
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const canSend = !disabled && value.trim().length > 0

  return (
    <div className="bg-white border-t border-gray-200 px-4 py-3">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-end gap-2 bg-white border border-gray-300 rounded-2xl shadow-sm focus-within:border-gray-400 transition-colors px-3 py-2">
          <textarea
            className="flex-1 resize-none bg-transparent text-sm text-gray-900 placeholder-gray-400 outline-none min-h-[24px] max-h-32 leading-6"
            placeholder="Type a message..."
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled && !streaming}
            rows={1}
            onInput={(e) => {
              const el = e.currentTarget
              el.style.height = "auto"
              el.style.height = Math.min(el.scrollHeight, 128) + "px"
            }}
          />

          {streaming ? (
            <button
              onClick={onStop}
              title="Stop generating"
              className="shrink-0 w-8 h-8 mb-0.5 rounded-full flex items-center justify-center bg-gray-900 hover:bg-gray-700 transition-colors"
            >
              {/* Filled square = stop icon */}
              <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="white">
                <rect x="3" y="3" width="18" height="18" rx="2" />
              </svg>
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!canSend}
              className="shrink-0 w-8 h-8 mb-0.5 rounded-full flex items-center justify-center transition-colors bg-gray-900 disabled:bg-gray-300"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
            </button>
          )}
        </div>
      </div>
    </div>
  )
}
