import { useEffect, useRef } from 'react'
import { motion } from 'framer-motion'
import { useChatStore } from '../../stores/useChatStore'
import { UserMessageBubble } from './messages/UserMessage'
import { FridayMessageBubble } from './messages/FridayMessage'
import { AgentResultCard } from './messages/AgentResultCard'
import { OsintResultCard } from './messages/OsintResultCard'
import { SystemMessageLine } from './messages/SystemMessage'
import { BriefingCard } from './messages/BriefingCard'
import { CameraQueryResult } from './messages/CameraQueryResult'
import type { Message } from '../../types'

function renderMessage(msg: Message) {
  switch (msg.type) {
    case 'user': return <UserMessageBubble message={msg} />
    case 'friday': return <FridayMessageBubble message={msg} />
    case 'agent_result': return <AgentResultCard message={msg} />
    case 'osint_result': return <OsintResultCard message={msg} />
    case 'system': return <SystemMessageLine message={msg} />
    case 'briefing': return <BriefingCard message={msg} />
    case 'camera_result': return <CameraQueryResult message={msg} />
    default: return null
  }
}

export function MessageList() {
  const messages = useChatStore((s) => s.messages)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages.length])

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-3">
      {messages.length === 0 && (
        <div className="h-full flex flex-col items-center justify-center text-center opacity-50">
          <span className="text-4xl mb-3">🛸</span>
          <p className="text-sm text-text-dim">Ask Friday anything…</p>
        </div>
      )}
      {messages.map((msg, i) => (
        <motion.div
          key={msg.id}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.15, delay: i > messages.length - 4 ? 0.05 : 0 }}
        >
          {renderMessage(msg)}
        </motion.div>
      ))}
      <div ref={bottomRef} />
    </div>
  )
}
