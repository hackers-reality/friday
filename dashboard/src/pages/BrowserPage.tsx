import { useState } from 'react'
import { NeonButton } from '../components/ui/NeonButton'
import { NeonCard } from '../components/ui/NeonCard'
import { Globe, ArrowLeft, ArrowRight, RefreshCw, Camera } from 'lucide-react'

export function BrowserPage() {
  const [url, setUrl] = useState('')
  const [screenshot, setScreenshot] = useState<string | null>(null)

  const navigate = () => {
    if (!url.trim()) return
    fetch('/api/browser/navigate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ url }) }).catch(() => {})
  }

  const grabScreenshot = async () => {
    try {
      const r = await fetch('/api/browser/screenshot')
      const data = await r.json()
      setScreenshot(data.image_base64)
    } catch { /* offline */ }
  }

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">Browser Control</h2>

      {/* URL Bar */}
      <div className="flex gap-2">
        <div className="flex-1 flex items-center gap-2 bg-friday-card border border-border-cyan rounded-lg px-3">
          <Globe size={14} className="text-text-dim shrink-0" />
          <input
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && navigate()}
            placeholder="https://..."
            className="flex-1 bg-transparent py-2 text-sm text-text-primary placeholder:text-text-muted outline-none"
          />
        </div>
        <NeonButton variant="primary" size="sm" onClick={navigate}>Go</NeonButton>
      </div>

      {/* Controls */}
      <div className="flex gap-1">
        {[
          { icon: <ArrowLeft size={14} />, label: 'Back' },
          { icon: <ArrowRight size={14} />, label: 'Forward' },
          { icon: <RefreshCw size={14} />, label: 'Refresh' },
          { icon: <Camera size={14} />, label: 'Screenshot', action: grabScreenshot },
        ].map((btn) => (
          <NeonButton key={btn.label} size="sm" onClick={btn.action} title={btn.label}>{btn.icon}</NeonButton>
        ))}
      </div>

      {/* Screenshot */}
      <NeonCard className="min-h-48">
        {screenshot ? (
          <img src={`data:image/png;base64,${screenshot}`} alt="Browser" className="w-full rounded-lg" />
        ) : (
          <div className="flex items-center justify-center h-48 opacity-50">
            <div className="text-center">
              <Globe size={32} className="text-text-dim mx-auto mb-2" />
              <p className="text-xs text-text-dim">Navigate to a page to see screenshot</p>
            </div>
          </div>
        )}
      </NeonCard>

      {/* AI Task */}
      <NeonCard>
        <h3 className="text-xs text-text-dim uppercase tracking-wider mb-2">AI Browser Task</h3>
        <textarea
          placeholder="Tell Friday what to do in the browser..."
          className="w-full bg-friday-input border border-border-cyan rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none resize-none h-16"
        />
        <NeonButton variant="primary" size="sm" className="mt-2">Execute</NeonButton>
      </NeonCard>
    </div>
  )
}
