import { useState, useEffect } from 'react'
import { getSidecars, type Sidecar } from '../api'

export default function SidecarPanel() {
  const [sidecars, setSidecars] = useState<Sidecar[]>([])
  const [showTokenForm, setShowTokenForm] = useState(false)

  useEffect(() => {
    const fetchSidecars = async () => {
      try {
        const s = await getSidecars()
        setSidecars(s)
      } catch { /* ignore */ }
    }
    fetchSidecars()
    const interval = setInterval(fetchSidecars, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-cyan-glow">Connected Sidecars</h3>
        <button
          onClick={() => setShowTokenForm(!showTokenForm)}
          className="px-3 py-1.5 text-xs bg-amber-glow/20 text-amber-glow border border-amber-glow/30 rounded-lg hover:shadow-[0_0_15px_rgba(245,158,11,0.15)] transition-all"
        >
          {showTokenForm ? 'Hide Token Mgmt' : '🔑 Token Management'}
        </button>
      </div>

      {showTokenForm && (
        <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
          <h4 className="text-xs font-semibold text-amber-glow mb-3">Generate Sidecar Token</h4>
          <div className="grid grid-cols-3 gap-3">
            <input type="text" placeholder="Sidecar name..." className="bg-[#1a1a3a] border border-cyan-muted/20 rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-cyan-glow" />
            <select className="bg-[#1a1a3a] border border-cyan-muted/20 rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-cyan-glow">
              <option>desktop</option>
              <option>browser</option>
              <option>system_monitor</option>
            </select>
            <button className="px-3 py-2 bg-amber-glow/20 text-amber-glow border border-amber-glow/30 rounded-lg text-sm hover:shadow-[0_0_15px_rgba(245,158,11,0.15)] transition-all">
              Generate Token
            </button>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sidecars.length === 0 ? (
          <div className="col-span-2 bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-8 text-center">
            <div className="text-4xl mb-3">🔌</div>
            <p className="text-sm text-text-muted">No sidecars connected</p>
            <p className="text-xs text-text-muted mt-1">Sidecars register automatically when deployed on remote machines</p>
          </div>
        ) : (
          sidecars.map((sc, i) => (
            <div key={i} className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <span className={`w-2 h-2 rounded-full ${sc.status === 'online' ? 'bg-neon-green shadow-[0_0_8px_#22c55e]' : 'bg-neon-red shadow-[0_0_8px_#ef4444]'}`} />
                  <span className="text-sm font-medium text-text-primary">{sc.name}</span>
                </div>
                <span className="text-xs text-text-muted">{sc.host}</span>
              </div>
              <div className="text-xs text-text-muted mb-2">
                Last heartbeat: {sc.last_heartbeat ? new Date(sc.last_heartbeat).toLocaleString() : 'N/A'}
              </div>
              <div className="flex flex-wrap gap-1">
                {(sc.capabilities ?? []).map((cap, j) => (
                  <span key={j} className="px-2 py-0.5 rounded text-xs bg-cyan-glow/10 text-cyan-glow border border-cyan-glow/20">
                    {cap}
                  </span>
                ))}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
