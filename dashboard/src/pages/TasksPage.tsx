import { NeonCard } from '../components/ui/NeonCard'
import { NeonBadge } from '../components/ui/NeonBadge'
import { EmptyState } from '../components/ui/EmptyState'
import clsx from 'clsx'

const COLUMNS = [
  { key: 'queued' as const, label: 'Queued', color: 'yellow' as const },
  { key: 'running' as const, label: 'Running', color: 'cyan' as const },
  { key: 'done' as const, label: 'Done', color: 'green' as const },
]

const DEMO_TASKS = [
  { id: '1', agent_name: 'Ghost', task_type: 'osint_scan', state: 'running' as const, payload: 'Scanning target IP 192.168.1.1', started_at: new Date().toISOString(), agent_id: 'ghost' },
  { id: '2', agent_name: 'Scholar', task_type: 'research', state: 'queued' as const, payload: 'Research latest AI papers', started_at: new Date().toISOString(), agent_id: 'scholar' },
  { id: '3', agent_name: 'Sentinel', task_type: 'monitor', state: 'done' as const, payload: 'Monitor port 443', started_at: new Date().toISOString(), agent_id: 'sentinel', duration_ms: 4500 },
]

export function TasksPage() {
  return (
    <div className="space-y-4">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">Task Board</h2>

      <div className="space-y-4">
        {COLUMNS.map((col) => {
          const tasks = DEMO_TASKS.filter((t) => t.state === col.key)
          return (
            <div key={col.key}>
              <div className="flex items-center gap-2 mb-2">
                <h3 className="text-xs uppercase tracking-wider text-text-dim">{col.label}</h3>
                <NeonBadge color={col.color} size="sm">{tasks.length}</NeonBadge>
              </div>
              {tasks.length === 0 ? (
                <div className="text-xs text-text-muted py-3 text-center border border-dashed border-border-cyan rounded-lg">Empty</div>
              ) : (
                <div className="space-y-2">
                  {tasks.map((task) => (
                    <NeonCard key={task.id} padding="p-3">
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-xs font-display text-text-primary">{task.agent_name}</span>
                        <NeonBadge color={col.color} size="sm">{task.task_type}</NeonBadge>
                      </div>
                      <p className="text-[11px] text-text-dim truncate">{task.payload}</p>
                      {task.duration_ms && (
                        <span className="text-[10px] text-text-muted font-mono mt-1 block">
                          {(task.duration_ms / 1000).toFixed(1)}s
                        </span>
                      )}
                    </NeonCard>
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
