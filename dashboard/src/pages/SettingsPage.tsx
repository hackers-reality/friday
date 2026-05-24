import { useEffect } from 'react'
import { useSettingsStore } from '../stores/useSettingsStore'
import { NeonCard } from '../components/ui/NeonCard'
import { NeonButton } from '../components/ui/NeonButton'
import { Settings as SettingsIcon, RefreshCw } from 'lucide-react'
import clsx from 'clsx'

const TABS = ['general', 'voice', 'agents', 'camera', 'browser', 'memory', 'notifications'] as const

function Toggle({ checked, onChange }: { checked: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!checked)}
      className={clsx('w-10 h-6 rounded-full transition-colors relative', checked ? 'bg-neon-cyan' : 'bg-friday-bg-deep border border-border-cyan')}
    >
      <span className={clsx('absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform', checked ? 'left-4.5' : 'left-0.5')} />
    </button>
  )
}

function SettingRow({ label, desc, children }: { label: string; desc?: string; children: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between py-3 border-b border-border-cyan/30">
      <div>
        <div className="text-sm text-text-primary">{label}</div>
        {desc && <div className="text-xs text-text-dim">{desc}</div>}
      </div>
      {children}
    </div>
  )
}

export function SettingsPage() {
  const { config, isDirty, activeTab, fetchConfig, updateSetting, setActiveTab, saveConfig } = useSettingsStore()

  useEffect(() => { fetchConfig() }, [fetchConfig])

  const handleRestart = () => {
    if (confirm('Restart FRIDAY?')) {
      fetch('/api/system/restart', { method: 'POST' }).catch(() => {})
    }
  }

  return (
    <div className="max-w-4xl mx-auto p-6 space-y-6">
      <div className="flex items-center gap-3">
        <SettingsIcon size={20} className="text-neon-cyan" />
        <h1 className="text-lg font-display text-neon-cyan tracking-wider">Settings</h1>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 overflow-x-auto">
        {TABS.map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={clsx(
              'px-3 py-1.5 rounded-lg text-xs font-medium transition-colors capitalize whitespace-nowrap',
              activeTab === tab ? 'bg-neon-cyan/10 text-neon-cyan border border-border-cyan' : 'text-text-dim hover:text-text-secondary',
            )}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <NeonCard>
        {!config ? (
          <div className="text-sm text-text-dim py-4">Loading config...</div>
        ) : (
          <>
            {activeTab === 'general' && (
              <div>
                <SettingRow label="Name" desc="Assistant display name">
                  <input value={config.general.name} onChange={(e) => updateSetting('general', 'name', e.target.value)} className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none w-40 text-right" />
                </SettingRow>
                <SettingRow label="Version" desc="Current version">
                  <span className="text-sm font-mono text-text-dim">{config.general.version}</span>
                </SettingRow>
                <SettingRow label="Model" desc="Default AI model">
                  <input value={config.general.model} onChange={(e) => updateSetting('general', 'model', e.target.value)} className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm font-mono text-text-primary outline-none w-56 text-right" />
                </SettingRow>
                <SettingRow label="Voice" desc="Enable voice input">
                  <Toggle checked={config.general.voice_enabled} onChange={(v) => updateSetting('general', 'voice_enabled', v)} />
                </SettingRow>
              </div>
            )}

            {activeTab === 'voice' && (
              <div>
                <SettingRow label="Wake Word"><input value={config.voice.wake_word} onChange={(e) => updateSetting('voice', 'wake_word', e.target.value)} className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none w-40 text-right" /></SettingRow>
                <SettingRow label="Voice Name"><input value={config.voice.voice_name} onChange={(e) => updateSetting('voice', 'voice_name', e.target.value)} className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none w-40 text-right" /></SettingRow>
                <SettingRow label="Sensitivity"><input type="range" min="0" max="1" step="0.1" value={config.voice.sensitivity} onChange={(e) => updateSetting('voice', 'sensitivity', parseFloat(e.target.value))} className="w-32" /></SettingRow>
              </div>
            )}

            {activeTab === 'agents' && (
              <div>
                <SettingRow label="Max Parallel"><input type="number" value={config.agents.max_parallel} onChange={(e) => updateSetting('agents', 'max_parallel', parseInt(e.target.value))} className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none w-20 text-right" /></SettingRow>
                <SettingRow label="Timeout (ms)"><input type="number" value={config.agents.default_timeout_ms} onChange={(e) => updateSetting('agents', 'default_timeout_ms', parseInt(e.target.value))} className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none w-28 text-right" /></SettingRow>
                <SettingRow label="Auto-Retry"><Toggle checked={config.agents.auto_retry} onChange={(v) => updateSetting('agents', 'auto_retry', v)} /></SettingRow>
              </div>
            )}

            {activeTab === 'camera' && (
              <div>
                <SettingRow label="Enabled"><Toggle checked={config.camera.enabled} onChange={(v) => updateSetting('camera', 'enabled', v)} /></SettingRow>
                <SettingRow label="Device Index"><input type="number" value={config.camera.device_index} onChange={(e) => updateSetting('camera', 'device_index', parseInt(e.target.value))} className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none w-20 text-right" /></SettingRow>
                <SettingRow label="FPS"><input type="number" value={config.camera.fps} onChange={(e) => updateSetting('camera', 'fps', parseInt(e.target.value))} className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none w-20 text-right" /></SettingRow>
                <SettingRow label="CV Pipeline"><Toggle checked={config.camera.cv_pipeline} onChange={(v) => updateSetting('camera', 'cv_pipeline', v)} /></SettingRow>
              </div>
            )}

            {activeTab === 'browser' && (
              <div>
                <SettingRow label="Backend">
                  <select value={config.browser.backend} onChange={(e) => updateSetting('browser', 'backend', e.target.value)} className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none">
                    <option value="auto">Auto</option><option value="playwright">Playwright</option><option value="pyppeteer">Pyppeteer</option>
                  </select>
                </SettingRow>
                <SettingRow label="Headless"><Toggle checked={config.browser.headless} onChange={(v) => updateSetting('browser', 'headless', v)} /></SettingRow>
              </div>
            )}

            {activeTab === 'memory' && (
              <div>
                <SettingRow label="Auto-Store"><Toggle checked={config.memory.auto_store} onChange={(v) => updateSetting('memory', 'auto_store', v)} /></SettingRow>
                <SettingRow label="Max Chunks"><input type="number" value={config.memory.max_chunks} onChange={(e) => updateSetting('memory', 'max_chunks', parseInt(e.target.value))} className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary outline-none w-28 text-right" /></SettingRow>
              </div>
            )}

            {activeTab === 'notifications' && (
              <div>
                <SettingRow label="Desktop"><Toggle checked={config.notifications.desktop} onChange={(v) => updateSetting('notifications', 'desktop', v)} /></SettingRow>
                <SettingRow label="Telegram"><Toggle checked={config.notifications.telegram} onChange={(v) => updateSetting('notifications', 'telegram', v)} /></SettingRow>
                <SettingRow label="Discord"><Toggle checked={config.notifications.discord} onChange={(v) => updateSetting('notifications', 'discord', v)} /></SettingRow>
                <SettingRow label="Webhook URL"><input value={config.notifications.webhook_url ?? ''} onChange={(e) => updateSetting('notifications', 'webhook_url', e.target.value)} placeholder="https://..." className="bg-friday-input border border-border-cyan rounded-lg px-3 py-1.5 text-sm text-text-primary placeholder:text-text-muted outline-none w-56 text-right" /></SettingRow>
              </div>
            )}
          </>
        )}
      </NeonCard>

      {/* Bottom actions */}
      <div className="flex items-center justify-between">
        <NeonButton variant="danger" size="sm" icon={<RefreshCw size={14} />} onClick={handleRestart}>Restart Friday</NeonButton>
        <NeonButton variant="primary" size="md" disabled={!isDirty} onClick={saveConfig}>
          {isDirty ? 'Save Changes' : 'Saved'}
        </NeonButton>
      </div>
    </div>
  )
}
