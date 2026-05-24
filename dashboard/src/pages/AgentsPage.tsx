import { useSystemStore } from '../stores/useSystemStore'
import { NeonCard } from '../components/ui/NeonCard'
import { NeonBadge } from '../components/ui/NeonBadge'
import { NeonButton } from '../components/ui/NeonButton'
import { ProgressBar } from '../components/ui/ProgressBar'
import { EmptyState } from '../components/ui/EmptyState'
import { Bot } from 'lucide-react'
import clsx from 'clsx'

export function AgentsPage() {
  const agents = useSystemStore((s) => s.agents)

  const statusColor: Record<string, string> = { idle: 'bg-neon-green', running: 'bg-neon-cyan animate-pulse', completed: 'bg-neon-green', failed: 'bg-neon-red', offline: 'bg-text-muted' }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-display text-neon-cyan tracking-wider">Agent Fleet</h2>
        <NeonButton variant="primary" size="sm" icon={<Bot size={14} />}>Dispatch</NeonButton>
      </div>

      {agents.length === 0 ? (
        <EmptyState icon="🤖" title="No Agents" description="No agents registered. Check your config.yaml." />
      ) : (
        <div className="grid grid-cols-1 gap-3">
          {agents.map((agent) => (
            <NeonCard key={agent.id} hover>
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-lg bg-neon-purple/10 border border-neon-purple/20 flex items-center justify-center shrink-0">
                  <Bot size={18} className="text-neon-purple" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={clsx('w-2 h-2 rounded-full shrink-0', statusColor[agent.status])} />
                    <h3 className="text-sm font-display text-text-primary tracking-wider truncate">{agent.display_name || agent.name}</h3>
                  </div>
                  <div className="flex flex-wrap gap-1 mb-2">
                    <NeonBadge color="purple" size="sm">{agent.model}</NeonBadge>
                    {agent.task_types.slice(0, 3).map((t) => (
                      <NeonBadge key={t} color="cyan" size="sm">{t}</NeonBadge>
                    ))}
                  </div>
                  <ProgressBar value={agent.success_rate} label="Success" showPercent color="green" />
                  <div className="text-[10px] text-text-dim font-mono mt-1">{agent.tasks_today} tasks today</div>
                </div>
              </div>
            </NeonCard>
          ))}
        </div>
      )}
    </div>
  )
}
