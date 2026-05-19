import { useState, useEffect } from 'react'
import Overview from './components/Overview'
import MemoryPanel from './components/MemoryPanel'
import VisionPanel from './components/VisionPanel'
import AgentPanel from './components/AgentPanel'
import SidecarPanel from './components/SidecarPanel'
import SystemPanel from './components/SystemPanel'
import SettingsPanel from './components/SettingsPanel'
import { getHealth } from './api'

const navItems = [
  { id: 'overview', label: 'Overview', icon: '🛸' },
  { id: 'memory', label: 'Memory', icon: '🧠' },
  { id: 'vision', label: 'Vision', icon: '👁️' },
  { id: 'agents', label: 'Agents', icon: '🤖' },
  { id: 'sidecars', label: 'Sidecars', icon: '🔌' },
  { id: 'system', label: 'System', icon: '📊' },
  { id: 'settings', label: 'Settings', icon: '⚙️' },
]

export default function App() {
  const [activePanel, setActivePanel] = useState('overview')
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [, setHealth] = useState<{ status: string; uptime: number; version: string } | null>(null)
  const [apiOnline, setApiOnline] = useState(false)
  const [version, setVersion] = useState('v1.0.0')

  useEffect(() => {
    const fetchHealth = async () => {
      try {
        const h = await getHealth()
        setHealth(h)
        setApiOnline(true)
        if (h.version) setVersion(h.version)
      } catch {
        setApiOnline(false)
      }
    }
    fetchHealth()
    const interval = setInterval(fetchHealth, 10000)
    return () => clearInterval(interval)
  }, [])

  const renderPanel = () => {
    switch (activePanel) {
      case 'overview': return <Overview />
      case 'memory': return <MemoryPanel />
      case 'vision': return <VisionPanel />
      case 'agents': return <AgentPanel />
      case 'sidecars': return <SidecarPanel />
      case 'system': return <SystemPanel />
      case 'settings': return <SettingsPanel />
      default: return <Overview />
    }
  }

  return (
    <div className="flex h-screen bg-cyber-darker overflow-hidden">
      {sidebarOpen && (
        <div className="w-64 bg-cyber-dark border-r border-cyan-muted/20 flex flex-col shrink-0">
          <div className="p-4 border-b border-cyan-muted/20">
            <h1 className="text-xl font-bold text-cyan-glow tracking-wider" style={{ textShadow: '0 0 20px #00d4ff66' }}>
              FRIDAY
            </h1>
            <span className="text-xs text-text-muted">{version}</span>
          </div>
          <nav className="flex-1 p-2 space-y-1">
            {navItems.map(item => (
              <button
                key={item.id}
                onClick={() => setActivePanel(item.id)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm transition-all ${
                  activePanel === item.id
                    ? 'bg-cyan-glow/10 text-cyan-glow border-l-2 border-cyan-glow shadow-[0_0_15px_rgba(0,212,255,0.15)]'
                    : 'text-text-muted hover:text-text-primary hover:bg-white/5'
                }`}
              >
                <span>{item.icon}</span>
                <span>{item.label}</span>
              </button>
            ))}
          </nav>
        </div>
      )}

      <div className="flex-1 flex flex-col min-w-0">
        <header className="h-14 bg-cyber-dark/80 backdrop-blur border-b border-cyan-muted/20 flex items-center justify-between px-6 shrink-0">
          <div className="flex items-center gap-4">
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="text-text-muted hover:text-cyan-glow text-xl"
            >
              ☰
            </button>
            <span className="text-sm font-medium text-text-primary capitalize">{activePanel}</span>
          </div>
          <div className="flex items-center gap-3">
            <span className="flex items-center gap-2 text-xs text-text-muted">
              <span className={`w-2 h-2 rounded-full ${apiOnline ? 'bg-neon-green shadow-[0_0_8px_#22c55e]' : 'bg-neon-red shadow-[0_0_8px_#ef4444]'}`} />
              {apiOnline ? 'API Online' : 'API Offline'}
            </span>
          </div>
        </header>
        <main className="flex-1 overflow-auto p-6">
          {renderPanel()}
        </main>
      </div>
    </div>
  )
}
