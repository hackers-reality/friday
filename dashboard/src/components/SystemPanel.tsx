import { useState, useEffect } from 'react'
import { getSystem, getDiagnostic, type SystemInfo, type Diagnostic } from '../api'

export default function SystemPanel() {
  const [system, setSystem] = useState<SystemInfo | null>(null)
  const [diag, setDiag] = useState<Diagnostic | null>(null)
  const [runningDoctor, setRunningDoctor] = useState(false)
  const [runningFix, setRunningFix] = useState(false)

  const fetchAll = async () => {
    try {
      const [s, d] = await Promise.all([getSystem(), getDiagnostic()])
      setSystem(s)
      setDiag(d)
    } catch { /* ignore */ }
  }

  useEffect(() => {
    fetchAll()
    const interval = setInterval(fetchAll, 5000)
    return () => clearInterval(interval)
  }, [])

  const runDoctor = async () => {
    setRunningDoctor(true)
    try {
      const res = await fetch('http://127.0.0.1:8090/api/diagnostic')
      const data = await res.json()
      setDiag(data)
    } catch { /* ignore */ }
    setRunningDoctor(false)
  }

  const runFix = async () => {
    setRunningFix(true)
    try {
      await fetch('http://127.0.0.1:8090/api/fix', { method: 'POST' })
      setTimeout(fetchAll, 2000)
    } catch { /* ignore */ }
    setRunningFix(false)
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-3 gap-4">
        {[
          { label: 'CPU', value: `${system?.cpu ?? 0}%`, color: (system?.cpu ?? 0) < 50 ? '#22c55e' : (system?.cpu ?? 0) < 80 ? '#f59e0b' : '#ef4444' },
          { label: 'RAM', value: `${system?.ram ?? 0}%`, color: (system?.ram ?? 0) < 50 ? '#22c55e' : (system?.ram ?? 0) < 80 ? '#f59e0b' : '#ef4444' },
          { label: 'Disk', value: `${system?.disk ?? 0}%`, color: (system?.disk ?? 0) < 50 ? '#22c55e' : (system?.disk ?? 0) < 80 ? '#f59e0b' : '#ef4444' },
        ].map(stat => (
          <div key={stat.label} className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4 text-center">
            <div className="text-3xl font-bold mb-1" style={{ color: stat.color, textShadow: `0 0 20px ${stat.color}66` }}>
              {stat.value}
            </div>
            <div className="text-xs text-text-muted">{stat.label}</div>
          </div>
        ))}
      </div>

      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-cyan-glow">Module Status</h3>
          <div className="flex gap-2">
            <button
              onClick={runDoctor}
              disabled={runningDoctor}
              className="px-3 py-1.5 text-xs bg-cyan-glow/20 text-cyan-glow border border-cyan-glow/30 rounded-lg hover:shadow-[0_0_15px_rgba(0,212,255,0.15)] transition-all disabled:opacity-50"
            >
              {runningDoctor ? 'Scanning...' : '🩺 Run Doctor'}
            </button>
            <button
              onClick={runFix}
              disabled={runningFix}
              className="px-3 py-1.5 text-xs bg-amber-glow/20 text-amber-glow border border-amber-glow/30 rounded-lg hover:shadow-[0_0_15px_rgba(245,158,11,0.15)] transition-all disabled:opacity-50"
            >
              {runningFix ? 'Fixing...' : '🔧 Auto-Fix'}
            </button>
          </div>
        </div>
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {(system?.modules ?? []).length > 0 ? (
            system!.modules.map((mod, i) => (
              <div key={i} className="flex items-center justify-between py-1.5 px-2 rounded hover:bg-white/5">
                <span className="text-sm text-text-primary">{mod.name}</span>
                <span className={`text-xs px-2 py-0.5 rounded ${mod.loaded ? 'bg-neon-green/10 text-neon-green' : 'bg-neon-red/10 text-neon-red'}`}>
                  {mod.loaded ? 'Loaded' : 'Missing'}
                </span>
              </div>
            ))
          ) : (
            <p className="text-sm text-text-muted italic">No module data</p>
          )}
        </div>
      </div>

      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-cyan-glow mb-3">Diagnostic Report</h3>
        {diag ? (
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className={`w-2 h-2 rounded-full ${diag.doctor_ok ? 'bg-neon-green' : 'bg-neon-red'}`} />
              <span className="text-sm text-text-primary">
                {diag.doctor_ok ? 'All systems nominal' : 'Issues detected'}
              </span>
            </div>
            {(diag.issues ?? []).length > 0 && (
              <ul className="list-disc list-inside space-y-1">
                {diag.issues.map((issue, i) => (
                  <li key={i} className="text-sm text-amber-glow">{issue}</li>
                ))}
              </ul>
            )}
            <div className="mt-3 max-h-32 overflow-y-auto space-y-1">
              {(diag.logs ?? []).slice(-20).map((log, i) => (
                <div key={i} className="text-xs text-text-muted">
                  <span className={log.level === 'ERROR' ? 'text-neon-red' : log.level === 'WARN' ? 'text-amber-glow' : ''}>
                    [{log.level}]
                  </span>
                  {' '}{log.message}
                </div>
              ))}
            </div>
          </div>
        ) : (
          <p className="text-sm text-text-muted italic">Run doctor to see diagnostic report</p>
        )}
      </div>
    </div>
  )
}
