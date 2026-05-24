import { useNavigate } from 'react-router-dom'
import { useSystemStore } from '../stores/useSystemStore'
import { StatCard } from '../components/ui/StatCard'
import { Bot, Monitor, Brain, Clock } from 'lucide-react'

export function ChatPage() {
  const navigate = useNavigate()
  const sys = useSystemStore((s) => s.systemStatus)

  const quickLinks = [
    { icon: '💬', label: 'Chat', desc: 'Natural conversation', path: '/' },
    { icon: '🔍', label: 'OSINT', desc: 'Intelligence gathering', path: '/osint' },
    { icon: '🧠', label: 'Memory', desc: 'Vector memory store', path: '/memory' },
    { icon: '🤖', label: 'Agents', desc: 'Agent orchestration', path: '/agents' },
    { icon: '📊', label: 'Analytics', desc: 'System monitoring', path: '/analytics' },
    { icon: '🛡️', label: 'Security', desc: 'Alert monitoring', path: '/security' },
  ]

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">Overview</h2>
      <div className="grid grid-cols-2 gap-3">
        <StatCard label="Agents Active" value={sys?.agents_active ?? 0} icon={<Bot size={14} />} />
        <StatCard label="Devices Online" value={sys?.devices_online ?? 0} icon={<Monitor size={14} />} />
        <StatCard label="Memory Chunks" value={sys?.memory_chunks ?? 0} icon={<Brain size={14} />} />
        <StatCard label="Uptime" value={sys ? `${Math.floor(sys.uptime / 3600)}h` : '—'} icon={<Clock size={14} />} />
      </div>

      <h3 className="text-xs text-text-dim uppercase tracking-wider mt-4">Quick Access</h3>
      <div className="grid grid-cols-2 gap-2">
        {quickLinks.map((item) => (
          <button
            key={item.label}
            onClick={() => navigate(item.path)}
            className="bg-friday-card border border-border-cyan rounded-xl p-3 text-left hover:border-border-cyan-hover transition-all card-hover"
          >
            <span className="text-xl block mb-1">{item.icon}</span>
            <h4 className="text-xs font-display text-neon-cyan tracking-wider">{item.label}</h4>
            <p className="text-[10px] text-text-dim">{item.desc}</p>
          </button>
        ))}
      </div>
    </div>
  )
}
