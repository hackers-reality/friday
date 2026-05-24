import { Mic } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import type { UserMessage } from '../../../types'

interface Props { message: UserMessage }

export function UserMessageBubble({ message }: Props) {
  return (
    <div className="flex justify-end">
      <div className="max-w-[70%] bg-friday-card border border-border-cyan rounded-2xl rounded-tr-sm px-4 py-2.5">
        <p className="text-sm text-text-primary whitespace-pre-wrap">{message.content}</p>
        <div className="flex items-center justify-end gap-1.5 mt-1.5">
          {message.voice_input && <Mic size={10} className="text-text-muted" />}
          <span className="text-[10px] text-text-muted font-mono">
            {formatDistanceToNow(new Date(message.timestamp), { addSuffix: true })}
          </span>
        </div>
      </div>
    </div>
  )
}
