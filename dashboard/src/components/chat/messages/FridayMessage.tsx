import { useState } from 'react'
import { Copy, Check } from 'lucide-react'
import { marked } from 'marked'
import DOMPurify from 'dompurify'
import type { FridayMessage } from '../../../types'

interface Props { message: FridayMessage }

export function FridayMessageBubble({ message }: Props) {
  const [copied, setCopied] = useState(false)

  const html = DOMPurify.sanitize(marked.parse(message.content || '') as string)

  const handleCopy = () => {
    navigator.clipboard.writeText(message.content).catch(() => {})
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="flex gap-3 group">
      {/* Avatar */}
      <div className="w-7 h-7 rounded-lg bg-friday-card border border-neon-cyan/30 flex items-center justify-center shrink-0 mt-0.5">
        <span className="text-xs font-bold text-neon-cyan">F</span>
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div
          className="friday-prose text-sm text-text-primary"
          dangerouslySetInnerHTML={{ __html: html }}
        />
        {message.isStreaming && (
          <span className="inline-block w-2 h-4 bg-neon-cyan animate-blink ml-0.5" />
        )}

        {/* Hover actions */}
        <div className="opacity-0 group-hover:opacity-100 transition-opacity mt-1">
          <button
            onClick={handleCopy}
            className="text-text-muted hover:text-neon-cyan transition-colors p-1"
            title="Copy"
          >
            {copied ? <Check size={12} className="text-neon-green" /> : <Copy size={12} />}
          </button>
        </div>
      </div>
    </div>
  )
}
