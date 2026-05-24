import { useSystemStore } from '../../stores/useSystemStore'
import { MessageList } from './MessageList'
import { ChatInput } from './ChatInput'

export function ChatPanel() {
  const connected = useSystemStore((s) => s.connected)

  return (
    <div className="h-full flex flex-col bg-friday-bg">
      {/* Header */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-border-cyan shrink-0">
        <span
          className={`w-2 h-2 rounded-full ${connected ? 'bg-neon-green' : 'bg-neon-red animate-pulse'}`}
        />
        <h3 className="text-sm font-display text-neon-cyan tracking-wider">Neural Link</h3>
        <span className="text-[10px] text-text-muted font-mono ml-auto">
          {connected ? 'Online' : 'Offline'}
        </span>
      </div>

      {/* Messages */}
      <MessageList />

      {/* Input */}
      <ChatInput />
    </div>
  )
}
