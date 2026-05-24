import { useState, useEffect } from 'react'
import { NeonCard } from '../components/ui/NeonCard'
import { NeonBadge } from '../components/ui/NeonBadge'
import { NeonButton } from '../components/ui/NeonButton'
import { Play, Pause, Plus } from 'lucide-react'
import type { SchedulerJob } from '../types'

export function SchedulerPage() {
  const [jobs, setJobs] = useState<SchedulerJob[]>([])
  const [showAdd, setShowAdd] = useState(false)
  const [newName, setNewName] = useState('')
  const [newSchedule, setNewSchedule] = useState('')
  const [newTarget, setNewTarget] = useState('')

  useEffect(() => {
    fetch('/api/scheduler/jobs').then((r) => r.json()).then(setJobs).catch(() => {})
  }, [])

  const toggleJob = async (id: string) => {
    await fetch(`/api/scheduler/${id}/toggle`, { method: 'POST' }).catch(() => {})
    setJobs((j) => j.map((job) => job.id === id ? { ...job, status: job.status === 'active' ? 'paused' : 'active' } : job))
  }

  const runJob = async (id: string) => { await fetch(`/api/scheduler/${id}/run`, { method: 'POST' }).catch(() => {}) }

  const statusColor: Record<string, 'green' | 'yellow' | 'red'> = { active: 'green', paused: 'yellow', failed: 'red' }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-display text-neon-cyan tracking-wider">Scheduler</h2>
        <NeonButton variant="primary" size="sm" icon={<Plus size={14} />} onClick={() => setShowAdd(!showAdd)}>Add Job</NeonButton>
      </div>

      {/* Add job form */}
      {showAdd && (
        <NeonCard>
          <div className="space-y-2">
            <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="Job name" className="w-full bg-friday-input border border-border-cyan rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none" />
            <input value={newSchedule} onChange={(e) => setNewSchedule(e.target.value)} placeholder="Cron expression (e.g. */5 * * * *)" className="w-full bg-friday-input border border-border-cyan rounded-lg px-3 py-2 text-sm font-mono text-text-primary placeholder:text-text-muted outline-none" />
            <input value={newTarget} onChange={(e) => setNewTarget(e.target.value)} placeholder="Target command" className="w-full bg-friday-input border border-border-cyan rounded-lg px-3 py-2 text-sm text-text-primary placeholder:text-text-muted outline-none" />
            <NeonButton variant="primary" size="sm">Create</NeonButton>
          </div>
        </NeonCard>
      )}

      {/* Jobs list */}
      {jobs.length === 0 ? (
        <div className="text-sm text-text-dim text-center py-8">No scheduled jobs</div>
      ) : (
        <div className="space-y-2">
          {jobs.map((job) => (
            <NeonCard key={job.id} padding="p-3">
              <div className="flex items-center justify-between mb-1">
                <span className="text-sm text-text-primary font-display tracking-wider">{job.name}</span>
                <NeonBadge color={statusColor[job.status] ?? 'yellow'} size="sm">{job.status}</NeonBadge>
              </div>
              <div className="text-[10px] text-text-dim font-mono mb-2">{job.schedule}</div>
              <div className="flex items-center gap-1">
                <button onClick={() => toggleJob(job.id)} className="text-text-dim hover:text-neon-cyan transition-colors p-1" title={job.status === 'active' ? 'Pause' : 'Resume'}>
                  {job.status === 'active' ? <Pause size={14} /> : <Play size={14} />}
                </button>
                <button onClick={() => runJob(job.id)} className="text-text-dim hover:text-neon-green transition-colors p-1" title="Run Now">
                  <Play size={14} />
                </button>
              </div>
            </NeonCard>
          ))}
        </div>
      )}
    </div>
  )
}
