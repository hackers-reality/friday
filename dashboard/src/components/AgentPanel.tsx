import { useState, useEffect } from 'react'

interface AgentInfo {
  name: string
  role: string
  status: string
  task: string
  result?: string
  current_step?: string
  steps_completed?: number
  total_steps?: number
  thought_process?: string[]
  created_at: string
  completed_at?: string
  is_running?: boolean
  elapsed_seconds?: number
}

interface AgentForm {
  name: string
  role: string
  task: string
}

const ROLE_CONFIG: Record<string, { label: string; color: string; icon: string }> = {
  researcher: { label: 'Researcher', color: '#a855f7', icon: '🔬' },
  coder: { label: 'Coder', color: '#22c55e', icon: '💻' },
  analyst: { label: 'Analyst', color: '#f59e0b', icon: '📊' },
  reviewer: { label: 'Reviewer', color: '#00d4ff', icon: '👁️' },
  integrator: { label: 'Integrator', color: '#ef4444', icon: '🔗' },
  planner: { label: 'Planner', color: '#ec4899', icon: '📋' },
  general: { label: 'General', color: '#64748b', icon: '🤖' },
}

const STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  spawning: { label: 'Spawning', color: '#f59e0b' },
  running: { label: 'Working', color: '#22c55e' },
  completed: { label: 'Completed', color: '#00d4ff' },
  failed: { label: 'Failed', color: '#ef4444' },
  idle: { label: 'Idle', color: '#64748b' },
}

type FilterTab = 'all' | 'running' | 'idle' | 'completed'

export default function AgentPanel() {
  const [agents, setAgents] = useState<AgentInfo[]>([])
  const [form, setForm] = useState<AgentForm>({ name: '', role: 'researcher', task: '' })
  const [spawning, setSpawning] = useState(false)
  const [selectedAgent, setSelectedAgent] = useState<AgentInfo | null>(null)
  const [filterTab, setFilterTab] = useState<FilterTab>('all')

  const fetchAgents = async () => {
    try {
      const res = await fetch('http://127.0.0.1:8090/api/agents')
      const data = await res.json()
      setAgents(data?.agents ?? [])
    } catch { /* ignore */ }
  }

  useEffect(() => {
    fetchAgents()
    const interval = setInterval(fetchAgents, 3000)
    return () => clearInterval(interval)
  }, [])

  const spawnAgent = async () => {
    if (!form.name || !form.task) return
    setSpawning(true)
    try {
      await fetch('http://127.0.0.1:8090/api/agents/spawn', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: form.name, role: form.role, task: form.task }),
      })
      setForm({ name: '', role: 'researcher', task: '' })
      setTimeout(fetchAgents, 1000)
    } catch { /* ignore */ }
    setSpawning(false)
  }

  const filteredAgents = agents.filter(a => {
    if (filterTab === 'all') return true
    if (filterTab === 'running') return a.status === 'running' || a.status === 'spawning'
    if (filterTab === 'idle') return a.status === 'idle' || a.status === 'failed'
    if (filterTab === 'completed') return a.status === 'completed'
    return true
  })

  const status = (s: string) => STATUS_CONFIG[s] ?? { label: s, color: '#64748b' }
  const roleCfg = (r: string) => ROLE_CONFIG[r] ?? ROLE_CONFIG.general

  const countByStatus = (s: string) => agents.filter(a => a.status === s).length
  const runningCount = countByStatus('running') + countByStatus('spawning')

  const tabs: { key: FilterTab; label: string; count: number }[] = [
    { key: 'all', label: 'All', count: agents.length },
    { key: 'running', label: 'Working', count: runningCount },
    { key: 'idle', label: 'Idle', count: countByStatus('idle') + countByStatus('failed') },
    { key: 'completed', label: 'Completed', count: countByStatus('completed') },
  ]

  if (selectedAgent) {
    const role = roleCfg(selectedAgent.role)
    const st = status(selectedAgent.status)
    return (
      <div className="space-y-4">
        <button
          onClick={() => setSelectedAgent(null)}
          className="flex items-center gap-2 text-sm text-cyan-glow hover:text-cyan-muted transition-colors"
        >
          ← Back to Agents
        </button>

        <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-6">
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="text-3xl">{role.icon}</div>
              <div>
                <h2 className="text-xl font-bold text-text-primary">{selectedAgent.name}</h2>
                <p className="text-sm text-text-muted">{role.label} Agent</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full" style={{ background: st.color, boxShadow: `0 0 12px ${st.color}` }} />
              <span className="text-sm font-medium" style={{ color: st.color }}>{st.label}</span>
            </div>
          </div>

          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-[#1a1a3a]/50 rounded-lg p-3">
              <div className="text-xs text-text-muted mb-1">Created</div>
              <div className="text-sm text-text-primary">{new Date(selectedAgent.created_at).toLocaleString()}</div>
            </div>
            <div className="bg-[#1a1a3a]/50 rounded-lg p-3">
              <div className="text-xs text-text-muted mb-1">Elapsed</div>
              <div className="text-sm text-text-primary">
                {selectedAgent.elapsed_seconds != null ? `${Math.round(selectedAgent.elapsed_seconds)}s` : '--'}
              </div>
            </div>
            <div className="bg-[#1a1a3a]/50 rounded-lg p-3">
              <div className="text-xs text-text-muted mb-1">Progress</div>
              <div className="text-sm text-text-primary">
                {selectedAgent.total_steps != null
                  ? `${selectedAgent.steps_completed ?? 0} / ${selectedAgent.total_steps} steps`
                  : '--'}
              </div>
            </div>
          </div>

          {selectedAgent.total_steps != null && selectedAgent.total_steps > 0 && (
            <div className="mb-6">
              <div className="w-full bg-[#1a1a3a] rounded-full h-2 overflow-hidden">
                <div
                  className="h-full rounded-full transition-all duration-500"
                  style={{
                    width: `${Math.min(100, ((selectedAgent.steps_completed ?? 0) / selectedAgent.total_steps) * 100)}%`,
                    background: `linear-gradient(90deg, ${st.color}, ${st.color}88)`,
                    boxShadow: `0 0 12px ${st.color}`,
                  }}
                />
              </div>
            </div>
          )}

          <div className="mb-6">
            <h4 className="text-xs font-semibold text-cyan-glow mb-2 uppercase tracking-wider">Mission</h4>
            <div className="bg-[#1a1a3a]/30 rounded-lg p-3 border border-cyan-muted/10">
              <p className="text-sm text-text-primary leading-relaxed">{selectedAgent.task}</p>
            </div>
          </div>

          {selectedAgent.current_step && (
            <div className="mb-6">
              <h4 className="text-xs font-semibold text-cyan-glow mb-2 uppercase tracking-wider">Currently Working On</h4>
              <div className="bg-cyan-glow/5 rounded-lg p-3 border border-cyan-glow/20 flex items-center gap-3">
                <div className="w-2 h-2 rounded-full bg-cyan-glow animate-pulse shadow-[0_0_8px_#00d4ff]" />
                <p className="text-sm text-cyan-glow">{selectedAgent.current_step}</p>
              </div>
            </div>
          )}

          {selectedAgent.thought_process && selectedAgent.thought_process.length > 0 && (
            <div className="mb-6">
              <h4 className="text-xs font-semibold text-cyan-glow mb-2 uppercase tracking-wider">Thought Process</h4>
              <div className="space-y-1 max-h-48 overflow-y-auto">
                {selectedAgent.thought_process.map((step, i) => (
                  <div key={i} className="flex items-start gap-2 text-sm text-text-muted">
                    <span className="text-cyan-glow mt-0.5">▸</span>
                    <span>{step}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {selectedAgent.result && (
            <div>
              <h4 className="text-xs font-semibold text-cyan-glow mb-2 uppercase tracking-wider">Result</h4>
              <div className="bg-black/30 rounded-lg p-4 border border-cyan-muted/10">
                <pre className="text-sm text-text-primary whitespace-pre-wrap font-sans leading-relaxed">{selectedAgent.result}</pre>
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-cyan-glow mb-4">Spawn Agent</h3>
        <div className="grid grid-cols-5 gap-3">
          <input
            type="text"
            placeholder="Agent name..."
            value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
            className="bg-[#1a1a3a] border border-cyan-muted/20 rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-cyan-glow"
          />
          <select
            value={form.role}
            onChange={e => setForm(f => ({ ...f, role: e.target.value }))}
            className="bg-[#1a1a3a] border border-cyan-muted/20 rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-cyan-glow"
          >
            {Object.entries(ROLE_CONFIG).map(([k, v]) => (
              <option key={k} value={k}>{v.icon} {v.label}</option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Task description..."
            value={form.task}
            onChange={e => setForm(f => ({ ...f, task: e.target.value }))}
            className="bg-[#1a1a3a] border border-cyan-muted/20 rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-cyan-glow col-span-2"
          />
          <button
            onClick={spawnAgent}
            disabled={spawning || !form.name || !form.task}
            className="px-4 py-2 bg-cyan-glow/20 text-cyan-glow border border-cyan-glow/30 rounded-lg text-sm font-medium hover:shadow-[0_0_20px_rgba(0,212,255,0.2)] transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
          >
            {spawning ? (
              <><span className="w-4 h-4 border-2 border-cyan-glow border-t-transparent rounded-full animate-spin" /> Spawning...</>
            ) : (
              <><span>🚀</span> Deploy</>
            )}
          </button>
        </div>
      </div>

      {agents.length > 0 && (
        <div className="flex items-center gap-2">
          {tabs.map(tab => (
            <button
              key={tab.key}
              onClick={() => setFilterTab(tab.key)}
              className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
                filterTab === tab.key
                  ? 'bg-cyan-glow/20 text-cyan-glow border border-cyan-glow/30'
                  : 'text-text-muted hover:text-text-primary border border-transparent'
              }`}
            >
              {tab.label}
              {tab.count > 0 && (
                <span className="ml-1.5 px-1.5 py-0.5 rounded-full bg-[#1a1a3a] text-[10px]">{tab.count}</span>
              )}
            </button>
          ))}
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {filteredAgents.length === 0 ? (
          <div className="col-span-2 bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-8 text-center">
            <div className="text-4xl mb-3">🤖</div>
            <p className="text-sm text-text-muted">
              {filterTab === 'all'
                ? 'No agents yet. Spawn one above.'
                : `No ${filterTab} agents.`}
            </p>
          </div>
        ) : (
          filteredAgents.map((agent, i) => {
            const role = roleCfg(agent.role)
            const st = status(agent.status)
            const progress = agent.total_steps != null && agent.total_steps > 0
              ? ((agent.steps_completed ?? 0) / agent.total_steps) * 100
              : 0

            return (
              <div
                key={i}
                onClick={() => setSelectedAgent(agent)}
                className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4 hover:border-cyan-glow/40 hover:shadow-[0_0_20px_rgba(0,212,255,0.08)] transition-all cursor-pointer group"
              >
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="text-xl">{role.icon}</div>
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-text-primary group-hover:text-cyan-glow transition-colors">{agent.name}</span>
                        <span className="text-xs text-text-muted">· {role.label}</span>
                      </div>
                      <div className="flex items-center gap-2 mt-1">
                        <span className="w-1.5 h-1.5 rounded-full" style={{ background: st.color, boxShadow: `0 0 6px ${st.color}` }} />
                        <span className="text-xs" style={{ color: st.color }}>{st.label}</span>
                        {agent.elapsed_seconds != null && (
                          <span className="text-xs text-text-muted">· {Math.round(agent.elapsed_seconds)}s</span>
                        )}
                      </div>
                    </div>
                  </div>
                  <span className="text-xs text-text-muted opacity-0 group-hover:opacity-100 transition-opacity">Click to inspect ▸</span>
                </div>

                <p className="text-xs text-text-muted line-clamp-2 mb-2">{agent.task}</p>

                {agent.current_step && agent.status === 'running' && (
                  <div className="flex items-center gap-2 text-xs text-cyan-glow mb-2">
                    <span className="w-1.5 h-1.5 rounded-full bg-cyan-glow animate-pulse" />
                    <span className="truncate">{agent.current_step}</span>
                  </div>
                )}

                {progress > 0 && (
                  <div className="w-full bg-[#1a1a3a] rounded-full h-1.5 overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all duration-500"
                      style={{
                        width: `${Math.min(100, progress)}%`,
                        background: `linear-gradient(90deg, ${st.color}, ${st.color}88)`,
                      }}
                    />
                  </div>
                )}

                {(agent.steps_completed != null || agent.total_steps != null) && (
                  <div className="mt-1 text-[10px] text-text-muted">
                    {agent.steps_completed ?? 0} / {agent.total_steps ?? 0} steps
                  </div>
                )}
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
