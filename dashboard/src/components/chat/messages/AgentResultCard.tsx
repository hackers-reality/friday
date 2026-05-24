import { motion } from 'framer-motion'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { AgentResultMessage } from '../../../types'

interface Props { message: AgentResultMessage }

export function AgentResultCard({ message }: Props) {
  const html = DOMPurify.sanitize(marked.parse(message.content || '') as string)
  const dur = message.duration_ms < 1000
    ? `${message.duration_ms}ms`
    : `${(message.duration_ms / 1000).toFixed(1)}s`

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      className="bg-friday-card border border-neon-cyan/20 rounded-xl p-4"
    >
      {/* Header */}
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span className="font-display text-lg text-neon-cyan tracking-wider">{message.agent_name}</span>
        <span className="text-[10px] font-mono bg-neon-purple/20 text-neon-purple px-2 py-0.5 rounded-full">
          {message.model}
        </span>
        <span className="text-[10px] font-mono bg-neon-cyan/10 text-neon-cyan px-2 py-0.5 rounded-full">
          {message.task_type}
        </span>
        <span className="text-[10px] font-mono text-text-dim ml-auto">{dur}</span>
      </div>

      {/* Body */}
      <div className="friday-prose text-sm" dangerouslySetInnerHTML={{ __html: html }} />

      {/* Footer */}
      <div className="flex items-center gap-2 mt-3 pt-2 border-t border-border-cyan">
        <span
          className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
            message.status === 'completed'
              ? 'bg-neon-green/20 text-neon-green'
              : 'bg-neon-red/20 text-neon-red'
          }`}
        >
          {message.status}
        </span>
      </div>
    </motion.div>
  )
}
