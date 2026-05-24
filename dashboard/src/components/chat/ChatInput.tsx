import { useState, useRef, useCallback, type KeyboardEvent } from 'react'
import { Paperclip, Camera, ArrowUp, Mic } from 'lucide-react'
import { useChatStore } from '../../stores/useChatStore'
import clsx from 'clsx'

export function ChatInput() {
  const [text, setText] = useState('')
  const [focused, setFocused] = useState(false)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const sendMessage = useChatStore((s) => s.sendMessage)
  const isStreaming = useChatStore((s) => s.isStreaming)

  const hasContent = text.trim().length > 0

  const handleSend = useCallback(() => {
    if (!hasContent || isStreaming) return
    sendMessage(text.trim())
    setText('')
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto'
    }
  }, [text, hasContent, isStreaming, sendMessage])

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleInput = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value)
    // Auto-resize
    const el = e.target
    el.style.height = 'auto'
    el.style.height = `${Math.min(el.scrollHeight, 150)}px`
  }

  return (
    <div
      className={clsx(
        'mx-3 mb-3 rounded-2xl border transition-colors duration-150',
        'bg-friday-card',
        focused ? 'border-neon-cyan/40' : 'border-border-cyan',
      )}
    >
      <textarea
        ref={textareaRef}
        value={text}
        onChange={handleInput}
        onKeyDown={handleKeyDown}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        placeholder="Ask Friday anything..."
        rows={1}
        className="w-full bg-transparent px-4 pt-3 pb-1 text-sm text-text-primary placeholder:text-text-muted resize-none outline-none"
      />
      <div className="flex items-center justify-between px-3 pb-2">
        <div className="flex items-center gap-1">
          <button
            className="p-1.5 text-text-dim hover:text-neon-cyan transition-colors rounded-lg"
            title="Attach file"
          >
            <Paperclip size={16} />
          </button>
          <button
            className="p-1.5 text-text-dim hover:text-neon-cyan transition-colors rounded-lg"
            title="Grab camera frame"
          >
            <Camera size={16} />
          </button>
          <button
            className="p-1.5 text-text-dim hover:text-neon-cyan transition-colors rounded-lg"
            title="Voice input"
          >
            <Mic size={16} />
          </button>
        </div>
        <button
          onClick={handleSend}
          disabled={!hasContent || isStreaming}
          className={clsx(
            'w-8 h-8 rounded-full flex items-center justify-center transition-all duration-150',
            hasContent && !isStreaming
              ? 'bg-neon-cyan text-friday-bg hover:brightness-110 active:scale-90'
              : 'bg-friday-card-hover text-text-muted cursor-not-allowed',
          )}
          title="Send message"
        >
          <ArrowUp size={16} />
        </button>
      </div>
    </div>
  )
}
