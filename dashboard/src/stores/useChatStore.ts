import { create } from 'zustand'
import type { Message } from '../types'

interface ChatState {
  messages: Message[]
  isStreaming: boolean
  streamingMessageId: string | null
  streamingContent: string

  addMessage: (msg: Message) => void
  appendToken: (token: string) => void
  finalizeStream: () => void
  loadHistory: () => Promise<void>
  clearChat: () => void
  sendMessage: (content: string, attachments?: File[]) => Promise<void>
}

export const useChatStore = create<ChatState>((set, get) => ({
  messages: [],
  isStreaming: false,
  streamingMessageId: null,
  streamingContent: '',

  addMessage: (msg) =>
    set((s) => ({ messages: [...s.messages, msg] })),

  appendToken: (token) =>
    set((s) => {
      const sid = s.streamingMessageId
      if (!sid) return s
      return {
        streamingContent: s.streamingContent + token,
        messages: s.messages.map((m) =>
          m.id === sid && m.type === 'friday'
            ? { ...m, content: s.streamingContent + token }
            : m,
        ),
      }
    }),

  finalizeStream: () =>
    set((s) => ({
      isStreaming: false,
      streamingMessageId: null,
      streamingContent: '',
      messages: s.messages.map((m) =>
        m.id === s.streamingMessageId && m.type === 'friday'
          ? { ...m, isStreaming: false }
          : m,
      ),
    })),

  loadHistory: async () => {
    try {
      const r = await fetch('/api/chat/history')
      if (!r.ok) return
      const data = (await r.json()) as Message[]
      set({ messages: data })
    } catch {
      /* offline */
    }
  },

  clearChat: () => set({ messages: [], isStreaming: false, streamingMessageId: null, streamingContent: '' }),

  sendMessage: async (content, attachments) => {
    const userMsg: Message = {
      id: crypto.randomUUID(),
      type: 'user',
      content,
      timestamp: new Date().toISOString(),
      attachments: attachments?.map((f) => ({
        id: crypto.randomUUID(),
        name: f.name,
        type: f.type,
        size: f.size,
      })),
    }
    get().addMessage(userMsg)

    const streamId = crypto.randomUUID()
    const fridayMsg: Message = {
      id: streamId,
      type: 'friday',
      content: '',
      timestamp: new Date().toISOString(),
      isStreaming: true,
    }
    set({ isStreaming: true, streamingMessageId: streamId, streamingContent: '' })
    get().addMessage(fridayMsg)

    try {
      const body: Record<string, unknown> = { message: content }
      if (attachments?.length) {
        const formData = new FormData()
        formData.append('message', content)
        attachments.forEach((f) => formData.append('files', f))
        await fetch('/api/chat/send', { method: 'POST', body: formData })
      } else {
        await fetch('/api/chat/send', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
      }
    } catch {
      get().appendToken('\n\n_Connection error. Please try again._')
      get().finalizeStream()
    }
  },
}))
