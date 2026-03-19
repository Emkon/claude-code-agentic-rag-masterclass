export interface Thread {
  id: string
  user_id: string
  title: string
  created_at: string
  updated_at: string
}

export interface Message {
  id: string
  thread_id: string
  user_id: string
  role: 'user' | 'assistant' | 'system'
  content: string
  created_at: string
}

export interface User {
  id: string
  email: string
}

export interface Document {
  id: string
  user_id: string
  filename: string
  storage_path: string
  size_bytes: number | null
  status: 'uploading' | 'parsing' | 'chunking' | 'embedding' | 'complete' | 'error'
  error_msg: string | null
  chunk_count: number
  created_at: string
  updated_at: string
}
