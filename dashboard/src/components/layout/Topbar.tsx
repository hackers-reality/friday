import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { Settings, Power } from 'lucide-react'
import { useVoiceStore } from '../../stores/useVoiceStore'
import { useSystemStore } from '../../stores/useSystemStore'
import { NotificationBell } from '../overlays/NotificationBell'
import clsx from 'clsx'

export function Topbar() {
  const navigate = useNavigate()
  const orbState = useVoiceStore((s) => s.orbState)
  const transcript = useVoiceStore((s) => s.transcript)
  const agents = useSystemStore((s) => s.agents)
  const devices = useSystemStore((s) => s.devices)
  const [clock, setClock] = useState('')
  const [shuttingDown, setShuttingDown] = useState(false)

  const activeAgents = agents.filter((a) => a.status === 'running').length
  const onlineDevices = devices.filter((d) => d.status === 'online').length

  useEffect(() => {
    const tick = () => {
      setClock(new Date().toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false }))
    }
    tick()
    const id = setInterval(tick, 1000)
    return () => clearInterval(id)
  }, [])

  const handleShutdown = async () => {
    if (!window.confirm('Shut down F.R.I.D.A.Y. completely? The dashboard will go offline.')) return
    setShuttingDown(true)
    try {
      await fetch('/api/system/shutdown', { method: 'POST' })
    } catch (_) {}
    setTimeout(() => {
      document.body.innerHTML = '<div style="background:#0A1118;color:#00f2fe;font-family:monospace;display:flex;align-items:center;justify-content:center;height:100vh;font-size:1.2rem;letter-spacing:0.1em;">F·R·I·D·A·Y · OFFLINE · Run <code style=\'margin:0 0.4em;padding:0.15em 0.4em;background:#111;border-radius:4px;\'>friday</code> to restart</div>'
    }, 1200)
  }

  const orbVariants = {
    idle: { scale: [1, 1.05, 1], boxShadow: '0 0 0px rgba(0,245,255,0)' },
    listening: { scale: [1, 1.1, 1], boxShadow: '0 0 24px rgba(0,245,255,0.5)' },
    speaking: { scale: [1, 1.08, 1], boxShadow: '0 0 20px rgba(180,0,255,0.4)' },
    error: { scale: [1, 0.95, 1], boxShadow: '0 0 16px rgba(255,0,60,0.5)' },
  }

  const orbColors: Record<string, string> = {
    idle: 'bg-gray-600',
    listening: 'bg-neon-cyan',
    speaking: 'bg-neon-purple',
    error: 'bg-neon-red',
  }

  return (
    <header className="h-12 flex items-center justify-between px-4 border-b border-border-cyan bg-friday-bg/80 backdrop-blur-sm shrink-0 z-30">
      {/* Left: Brand */}
      <div className="flex items-center gap-2">
        <h1 className="text-lg font-display text-neon-cyan tracking-[0.2em]" style={{ textShadow: '0 0 16px rgba(0,245,255,0.3)' }}>
          F·R·I·D·A·Y
        </h1>
        <span className="text-[10px] font-mono text-text-muted bg-friday-card px-1.5 py-0.5 rounded">v2.0</span>
      </div>

      {/* Center: Voice Orb */}
      <div className="flex flex-col items-center">
        <motion.button
          className={clsx('w-9 h-9 rounded-full cursor-pointer', orbColors[orbState])}
          animate={orbVariants[orbState]}
          transition={{ duration: orbState === 'idle' ? 2 : 0.6, repeat: Infinity, ease: 'easeInOut' }}
          onClick={() => {
            const isListening = orbState === 'listening'
            fetch(`/api/voice/push-to-talk/${isListening ? 'stop' : 'start'}`, { method: 'POST' }).catch(() => {})
          }}
          title={orbState === 'listening' ? 'Stop listening' : 'Push to talk'}
        />
        {transcript && (
          <span className="text-[10px] font-mono text-text-dim mt-0.5 max-w-48 truncate animate-fade-in">
            {transcript.slice(-60)}
          </span>
        )}
      </div>

      {/* Right: Status chips + controls */}
      <div className="flex items-center gap-3">
        {/* Agent chip */}
        <div className="flex items-center gap-1.5 text-xs text-text-secondary">
          <span className="w-1.5 h-1.5 rounded-full bg-neon-green animate-pulse" />
          <span className="font-mono">{activeAgents} active</span>
        </div>
        {/* Device chip */}
        <div className="flex items-center gap-1.5 text-xs text-text-secondary">
          <span className="w-1.5 h-1.5 rounded-full bg-neon-cyan" />
          <span className="font-mono">{onlineDevices} online</span>
        </div>
        {/* Clock */}
        <span className="text-xs font-mono text-text-dim hidden md:inline">{clock}</span>
        {/* Notification bell */}
        <NotificationBell />
        {/* Settings */}
        <button
          onClick={() => navigate('/settings')}
          className="text-text-dim hover:text-neon-cyan transition-colors"
          title="Settings"
        >
          <Settings size={16} />
        </button>
        {/* Shutdown FRIDAY */}
        <button
          onClick={handleShutdown}
          disabled={shuttingDown}
          className={clsx(
            'transition-colors',
            shuttingDown
              ? 'text-neon-red animate-pulse cursor-not-allowed'
              : 'text-text-dim hover:text-neon-red'
          )}
          title="Shut down F.R.I.D.A.Y."
        >
          <Power size={16} />
        </button>
      </div>
    </header>
  )
}
