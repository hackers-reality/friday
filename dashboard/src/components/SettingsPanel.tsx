import { useState } from 'react'

interface APIKey {
  key: string
  label: string
  value: string
  set: boolean
}

const defaultKeys: APIKey[] = [
  { key: 'GOOGLE_API_KEY', label: 'Gemini API', value: '', set: false },
  { key: 'PICOVOICE_ACCESS_KEY', label: 'Picovoice', value: '', set: false },
  { key: 'OPENCODE_ZEN_API_KEY', label: 'OpenCode Zen', value: '', set: false },
  { key: 'NVIDIA_NIM_API_KEY', label: 'NVIDIA NIM', value: '', set: false },
  { key: 'GROQ_API_KEY', label: 'Groq', value: '', set: false },
  { key: 'SPOTIFY_CLIENT_ID', label: 'Spotify', value: '', set: false },
]

const themePresets = [
  { name: 'Cyan Hologram', accent: '#00d4ff', glow: '0 0 30px rgba(0,212,255,0.3)' },
  { name: 'Neon Violet', accent: '#a855f7', glow: '0 0 30px rgba(168,85,247,0.3)' },
  { name: 'Amber Matrix', accent: '#f59e0b', glow: '0 0 30px rgba(245,158,11,0.3)' },
  { name: 'Crimson Alert', accent: '#ef4444', glow: '0 0 30px rgba(239,68,68,0.3)' },
]

export default function SettingsPanel() {
  const [apiKeys] = useState(defaultKeys)
  const [preset, setPreset] = useState(0)
  const [autoStart, setAutoStart] = useState(false)

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-cyan-glow mb-4">API Keys</h3>
        <div className="space-y-3">
          {apiKeys.map((ak) => (
            <div key={ak.key} className="flex items-center gap-3">
              <span className="text-sm text-text-primary w-32">{ak.label}</span>
              <div className="flex-1 relative">
                <input
                  type="password"
                  placeholder={ak.set ? '••••••••' : 'Not configured'}
                  className="w-full bg-[#1a1a3a] border border-cyan-muted/20 rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-cyan-glow"
                />
                <span className={`absolute right-3 top-1/2 -translate-y-1/2 w-2 h-2 rounded-full ${ak.set ? 'bg-neon-green shadow-[0_0_8px_#22c55e]' : 'bg-text-muted'}`} />
              </div>
              <button className="text-xs text-cyan-glow px-2 py-1 rounded hover:bg-cyan-glow/10 transition-all">Update</button>
            </div>
          ))}
        </div>
      </div>

      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-cyan-glow mb-4">Theme</h3>
        <div className="grid grid-cols-4 gap-3">
          {themePresets.map((p, i) => (
            <button
              key={p.name}
              onClick={() => setPreset(i)}
              className={`p-3 rounded-lg border transition-all ${
                preset === i ? 'border-transparent ring-2 ring-cyan-glow' : 'border-cyan-muted/20'
              }`}
              style={{ background: `${p.accent}15` }}
            >
              <div className="w-full h-8 rounded mb-2" style={{ background: p.accent, boxShadow: p.glow }} />
              <div className="text-xs text-text-primary">{p.name}</div>
            </button>
          ))}
        </div>
      </div>

      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-cyan-glow mb-4">Startup Behavior</h3>
        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer">
            <div
              onClick={() => setAutoStart(!autoStart)}
              className={`w-10 h-5 rounded-full transition-all relative cursor-pointer ${autoStart ? 'bg-cyan-glow' : 'bg-[#1a1a3a]'}`}
            >
              <div className={`w-4 h-4 rounded-full bg-white absolute top-0.5 transition-all ${autoStart ? 'left-5' : 'left-0.5'}`} />
            </div>
            <span className="text-sm text-text-primary">Auto-start FRIDAY with Windows</span>
          </label>
        </div>
      </div>
    </div>
  )
}
