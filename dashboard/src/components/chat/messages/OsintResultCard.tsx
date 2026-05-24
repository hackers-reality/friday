import { useNavigate } from 'react-router-dom'
import type { OsintResultMessage } from '../../../types'

interface Props { message: OsintResultMessage }

export function OsintResultCard({ message }: Props) {
  const navigate = useNavigate()

  return (
    <div className="bg-friday-card border-l-4 border-neon-purple rounded-xl p-4">
      <h4 className="text-sm font-display text-neon-purple tracking-wider mb-3">
        Ghost · OSINT Complete
      </h4>
      <div className="flex gap-6 mb-3">
        {[
          { label: 'Platforms', value: message.platforms_found },
          { label: 'Threats', value: message.threats },
          { label: 'Entities', value: message.entities },
        ].map((s) => (
          <div key={s.label}>
            <div className="text-xl font-display text-text-primary">{s.value}</div>
            <div className="text-[10px] text-text-dim uppercase tracking-wider">{s.label}</div>
          </div>
        ))}
      </div>
      <button
        onClick={() => navigate('/osint')}
        className="text-xs border border-neon-cyan text-neon-cyan px-3 py-1.5 rounded-lg hover:bg-neon-cyan/10 transition-colors"
      >
        View Knowledge Graph →
      </button>
    </div>
  )
}
