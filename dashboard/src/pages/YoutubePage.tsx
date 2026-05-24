import { useState, useEffect } from 'react'
import { StatCard } from '../components/ui/StatCard'
import { NeonCard } from '../components/ui/NeonCard'
import { NeonButton } from '../components/ui/NeonButton'
import { FridayAreaChart } from '../components/charts/AreaChart'
import type { YouTubeStats, YouTubeVideo } from '../types'

export function YoutubePage() {
  const [stats, setStats] = useState<YouTubeStats | null>(null)
  const [videos, setVideos] = useState<YouTubeVideo[]>([])
  const [desc, setDesc] = useState('')

  useEffect(() => {
    fetch('/api/youtube/stats').then((r) => r.json()).then(setStats).catch(() => {})
    fetch('/api/youtube/videos').then((r) => r.json()).then(setVideos).catch(() => {})
  }, [])

  const generateMeta = () => {
    if (!desc.trim()) return
    fetch('/api/youtube/generate-metadata', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ description: desc }) }).catch(() => {})
  }

  const chartData = Array.from({ length: 7 }, (_, i) => ({
    label: `Day ${i + 1}`,
    value: Math.floor(Math.random() * 1000 + (stats?.subscribers ?? 500)),
  }))

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">YouTube Studio</h2>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="Subscribers" value={stats?.subscribers ?? '—'} delta={stats?.subscribers_delta} />
        <StatCard label="Views" value={stats?.views ?? '—'} delta={stats?.views_delta} />
        <StatCard label="Videos" value={stats?.videos ?? '—'} />
        <StatCard label="Quota" value={stats ? `${stats.quota_used}/${stats.quota_limit}` : '—'} />
      </div>

      {/* Growth Chart */}
      <NeonCard>
        <h3 className="text-xs text-text-dim uppercase tracking-wider mb-2">Subscriber Growth</h3>
        <FridayAreaChart data={chartData} height={140} color="#00f5ff" />
      </NeonCard>

      {/* Top Videos */}
      <NeonCard>
        <h3 className="text-xs text-text-dim uppercase tracking-wider mb-2">Top Videos</h3>
        {videos.length === 0 ? (
          <p className="text-xs text-text-muted py-2">No video data available</p>
        ) : (
          <div className="space-y-1.5">
            {videos.slice(0, 5).map((v) => (
              <div key={v.video_id} className="flex items-center justify-between text-xs">
                <span className="text-text-primary truncate flex-1 mr-2">{v.title}</span>
                <span className="font-mono text-text-dim shrink-0">{v.views.toLocaleString()} views</span>
              </div>
            ))}
          </div>
        )}
      </NeonCard>

      {/* Metadata Generator */}
      <NeonCard>
        <h3 className="text-xs text-text-dim uppercase tracking-wider mb-2">AI Metadata Generator</h3>
        <textarea
          value={desc}
          onChange={(e) => setDesc(e.target.value)}
          placeholder="Describe your video content..."
          className="w-full bg-friday-input border border-border-cyan rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none resize-none h-16"
        />
        <NeonButton variant="primary" size="sm" className="mt-2" onClick={generateMeta}>Generate</NeonButton>
      </NeonCard>
    </div>
  )
}
