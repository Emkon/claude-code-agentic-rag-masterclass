import { supabase } from "./supabaseClient"
import type { Thread, Message, Document } from "@/types"


async function getAuthHeaders(): Promise<HeadersInit> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (!token) throw new Error("Not authenticated")
  return {
    "Content-Type": "application/json",
    Authorization: `Bearer ${token}`,
  }
}

async function getToken(): Promise<string> {
  const { data } = await supabase.auth.getSession()
  const token = data.session?.access_token
  if (!token) throw new Error("Not authenticated")
  return token
}

export async function createThread(title = "New Chat"): Promise<Thread> {
  const headers = await getAuthHeaders()
  const res = await fetch("/api/threads", {
    method: "POST",
    headers,
    body: JSON.stringify({ title }),
  })
  if (!res.ok) throw new Error("Failed to create thread")
  return res.json()
}

export async function listThreads(): Promise<Thread[]> {
  const headers = await getAuthHeaders()
  const res = await fetch("/api/threads", { headers })
  if (!res.ok) throw new Error("Failed to list threads")
  return res.json()
}

export async function deleteThread(threadId: string): Promise<void> {
  const headers = await getAuthHeaders()
  const res = await fetch(`/api/threads/${threadId}`, { method: "DELETE", headers })
  if (!res.ok) throw new Error("Failed to delete thread")
}

export async function updateThread(threadId: string, title: string): Promise<Thread> {
  const headers = await getAuthHeaders()
  const res = await fetch(`/api/threads/${threadId}`, {
    method: "PATCH",
    headers,
    body: JSON.stringify({ title }),
  })
  if (!res.ok) throw new Error("Failed to update thread")
  return res.json()
}

export async function listMessages(threadId: string): Promise<Message[]> {
  const headers = await getAuthHeaders()
  const res = await fetch(`/api/threads/${threadId}/messages`, { headers })
  if (!res.ok) throw new Error("Failed to list messages")
  return res.json()
}

export async function sendMessageStream(
  threadId: string,
  content: string,
  onChunk: (token: string) => void,
  onDone: () => void,
  onSources?: (count: number) => void,
  signal?: AbortSignal
): Promise<void> {
  const headers = await getAuthHeaders()
  const res = await fetch(`/api/threads/${threadId}/messages`, {
    method: "POST",
    headers,
    body: JSON.stringify({ content }),
    signal,
  })
  if (!res.ok) throw new Error("Failed to send message")

  const reader = res.body!.getReader()
  const decoder = new TextDecoder()

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    for (const line of decoder.decode(value).split("\n")) {
      if (line.startsWith("data: ")) {
        const payload = line.slice(6)
        if (payload === "[DONE]") {
          onDone()
          return
        }
        if (payload.startsWith("__sources:")) {
          const count = parseInt(payload.split(":")[1])
          onSources?.(count)
          continue
        }
        onChunk(payload)
      }
    }
  }
}

export async function listDocuments(): Promise<Document[]> {
  const headers = await getAuthHeaders()
  const res = await fetch("/api/documents", { headers })
  if (!res.ok) throw new Error("Failed to list documents")
  return res.json()
}

export async function uploadDocument(file: File): Promise<Document> {
  const token = await getToken()
  const formData = new FormData()
  formData.append("file", file)
  const res = await fetch("/api/documents", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: formData,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Upload failed" }))
    throw new Error(err.detail || "Upload failed")
  }
  return res.json()
}

export async function deleteDocument(documentId: string): Promise<void> {
  const headers = await getAuthHeaders()
  const res = await fetch(`/api/documents/${documentId}`, { method: "DELETE", headers })
  if (!res.ok) throw new Error("Failed to delete document")
}
