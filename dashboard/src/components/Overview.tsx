import { useState, useEffect, useRef } from 'react'
import { getHealth, getSystem, getTools, type SystemInfo, type ToolCall, type Health } from '../api'

function HolographicRing({ usage, color, label }: { usage: number; color: string; label: string }) {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return
    let angle = 0
    const animate = () => {
      ctx.clearRect(0, 0, 200, 200)
      angle += 0.01
      ctx.save()
      ctx.translate(100, 100)
      ctx.rotate(angle)
      ctx.beginPath()
      ctx.arc(0, 0, 70, 0, Math.PI * 2)
      ctx.strokeStyle = '#1a1a3a'
      ctx.lineWidth = 8
      ctx.stroke()
      ctx.beginPath()
      ctx.arc(0, 0, 70, 0, (Math.PI * 2 * usage) / 100)
      ctx.strokeStyle = color
      ctx.lineWidth = 8
      ctx.shadowColor = color
      ctx.shadowBlur = 20
      ctx.stroke()
      ctx.restore()
      ctx.fillStyle = color
      ctx.font = 'bold 20px monospace'
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      ctx.shadowColor = color
      ctx.shadowBlur = 15
      ctx.fillText(`${Math.round(usage)}%`, 100, 100)
      ctx.shadowBlur = 0
      ctx.fillStyle = '#64748b'
      ctx.font = '12px sans-serif'
      ctx.fillText(label, 100, 140)
      requestAnimationFrame(animate)
    }
    const frame = requestAnimationFrame(animate)
    return () => cancelAnimationFrame(frame)
  }, [usage, color, label])

  return <canvas ref={canvasRef} width={200} height={200} className="w-32 h-32" />
}

function getColor(value: number): string {
  if (value < 50) return '#22c55e'
  if (value < 80) return '#f59e0b'
  return '#ef4444'
}

export default function Overview() {
  const [health, setHealth] = useState<Health | null>(null)
  const [system, setSystem] = useState<SystemInfo | null>(null)
  const [tools, setTools] = useState<ToolCall[]>([])
  const [error, setError] = useState(false)

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [h, s, t] = await Promise.all([
          getHealth(),
          getSystem(),
          getTools(),
        ])
        setHealth(h)
        setSystem(s)
        setTools(t.slice(0, 10))
        setError(false)
      } catch {
        setError(true)
      }
    }
    fetchData()
    const interval = setInterval(fetchData, 5000)
    return () => clearInterval(interval)
  }, [])

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <div className="text-4xl mb-4">📡</div>
          <p className="text-text-muted">API Offline — Unable to connect to FRIDAY</p>
          <p className="text-xs text-text-muted mt-2">Retrying every 5 seconds...</p>
        </div>
      </div>
    )
  }

  const cpu = system?.cpu ?? 0
  const ram = system?.ram ?? 0
  const disk = system?.disk ?? 0

  const formatUptime = (sec: number) => {
    const d = Math.floor(sec / 86400)
    const h = Math.floor((sec % 86400) / 3600)
    const m = Math.floor((sec % 3600) / 60)
    return `${d}d ${h}h ${m}m`
  }

  return (
    <div className="space-y-6">
      <div className="flex justify-center gap-8">
        <HolographicRing usage={cpu} color={getColor(cpu)} label="CPU" />
        <HolographicRing usage={ram} color={getColor(ram)} label="RAM" />
        <HolographicRing usage={disk} color={getColor(disk)} label="Disk" />
      </div>

      <div className="grid grid-cols-4 gap-4">
        {[
          { label: 'Memory Profile', value: 'FRIDAY-v1', icon: '🧠' },
          { label: 'Active Sidecars', value: '3', icon: '🔌' },
          { label: 'Running Agents', value: '2', icon: '🤖' },
          { label: 'Uptime', value: health?.uptime ? formatUptime(health.uptime) : '--', icon: '⏱️' },
        ].map(stat => (
          <div key={stat.label} className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4 backdrop-blur">
            <div className="text-2xl mb-2">{stat.icon}</div>
            <div className="text-2xl font-bold text-cyan-glow">{stat.value}</div>
            <div className="text-xs text-text-muted mt-1">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-cyan-glow mb-3">Recent Activity</h3>
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {tools.map((t, i) => (
            <div key={i} className="flex items-center justify-between py-2 border-b border-cyan-muted/10 text-sm">
              <span className="text-text-primary">{t.tool}</span>
              <span className="text-text-muted text-xs">{new Date(t.timestamp).toLocaleString()}</span>
              <span className={`text-xs px-2 py-0.5 rounded ${
                t.status === 'success' ? 'bg-neon-green/10 text-neon-green' : 'bg-amber-glow/10 text-amber-glow'
              }`}>{t.status}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
