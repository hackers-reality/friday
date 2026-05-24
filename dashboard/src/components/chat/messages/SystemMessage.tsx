import type { SystemMessage } from '../../../types'

interface Props { message: SystemMessage }

export function SystemMessageLine({ message }: Props) {
  return (
    <div className="text-center py-2">
      <span className="text-xs font-mono text-neon-yellow/60 italic">
        {message.content}
      </span>
    </div>
  )
}
