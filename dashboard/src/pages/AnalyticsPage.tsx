import { useSystemStore } from '../stores/useSystemStore'
import { StatCard } from '../components/ui/StatCard'
import { NeonCard } from '../components/ui/NeonCard'
import { ProgressBar } from '../components/ui/ProgressBar'
import { FridayAreaChart } from '../components/charts/AreaChart'
import { FridayBarChart } from '../components/charts/BarChart'
import { Activity, Cpu, HardDrive, Clock } from 'lucide-react'

export function AnalyticsPage() {
  const sys = useSystemStore((s) => s.systemStatus)
  const agents = useSystemStore((s) => s.agents)

  const timelineData = Array.from({ length: 12 }, (_, i) => ({ label: `${i * 2}:00`, value: Math.floor(Math.random() * 50 + 10) }))
  const agentData = agents.slice(0, 6).map((a) => ({ label: a.name.slice(0, 8), value: a.tasks_today }))

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">Analytics</h2>

      {/* System metrics */}
      <div className="grid grid-cols-2 gap-2">
        <StatCard label="CPU" value={`${sys?.cpu ?? 0}%`} icon={<Cpu size={14} />} />
        <StatCard label="Memory" value={`${sys?.memory ?? 0}%`} icon={<Activity size={14} />} />
        <StatCard label="Disk" value={`${sys?.disk ?? 0}%`} icon={<HardDrive size={14} />} />
        <StatCard label="Uptime" value={sys ? `${Math.floor(sys.uptime / 3600)}h` : '—'} icon={<Clock size={14} />} />
      </div>

      {/* System gauges */}
      <NeonCard>
        <h3 className="text-xs text-text-dim uppercase tracking-wider mb-3">System Resources</h3>
        <div className="space-y-3">
          <ProgressBar value={sys?.cpu ?? 0} label="CPU" showPercent color={sys && sys.cpu > 80 ? 'red' : 'cyan'} />
          <ProgressBar value={sys?.memory ?? 0} label="Memory" showPercent color={sys && sys.memory > 80 ? 'red' : 'green'} />
          <ProgressBar value={sys?.disk ?? 0} label="Disk" showPercent color={sys && sys.disk > 90 ? 'red' : 'yellow'} />
        </div>
      </NeonCard>

      {/* Request timeline */}
      <NeonCard>
        <h3 className="text-xs text-text-dim uppercase tracking-wider mb-2">Requests (24h)</h3>
        <FridayAreaChart data={timelineData} height={120} color="#00f5ff" gradient />
      </NeonCard>

      {/* Agent performance */}
      {agentData.length > 0 && (
        <NeonCard>
          <h3 className="text-xs text-text-dim uppercase tracking-wider mb-2">Agent Tasks Today</h3>
          <FridayBarChart data={agentData} height={120} />
        </NeonCard>
      )}
    </div>
  )
}
