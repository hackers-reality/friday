import { useSystemStore } from '../stores/useSystemStore'
import { NeonCard } from '../components/ui/NeonCard'
import { NeonBadge } from '../components/ui/NeonBadge'
import { NeonButton } from '../components/ui/NeonButton'
import { ProgressBar } from '../components/ui/ProgressBar'
import { EmptyState } from '../components/ui/EmptyState'
import { Terminal } from 'lucide-react'
import { formatDistanceToNow } from 'date-fns'
import clsx from 'clsx'

export function DevicesPage() {
  const devices = useSystemStore((s) => s.devices)

  const platformIcon: Record<string, string> = { windows: '🪟', macos: '🍎', linux: '🐧', android: '🤖', ios: '📱' }

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">Devices</h2>

      {devices.length === 0 ? (
        <EmptyState icon="📱" title="No Devices" description="Connect sidecar devices to see them here" />
      ) : (
        <div className="space-y-3">
          {devices.map((dev) => (
            <NeonCard key={dev.name}>
              <div className="flex items-start gap-3">
                <span className="text-2xl">{platformIcon[dev.platform] ?? '💻'}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-2">
                    <span className={clsx('w-2 h-2 rounded-full', dev.status === 'online' ? 'bg-neon-green' : 'bg-text-muted')} />
                    <h3 className="text-sm font-display text-text-primary tracking-wider">{dev.name}</h3>
                    <NeonBadge color={dev.status === 'online' ? 'green' : 'red'} size="sm">{dev.status}</NeonBadge>
                  </div>

                  {/* Telemetry */}
                  <div className="space-y-1.5 mb-2">
                    <ProgressBar value={dev.telemetry.cpu} label="CPU" showPercent color="cyan" />
                    <ProgressBar value={dev.telemetry.ram} label="RAM" showPercent color="green" />
                    <ProgressBar value={dev.telemetry.disk} label="Disk" showPercent color="yellow" />
                  </div>

                  {/* Capabilities */}
                  <div className="flex flex-wrap gap-1 mb-2">
                    {dev.capabilities.map((cap) => (
                      <NeonBadge key={cap} color="purple" size="sm">{cap}</NeonBadge>
                    ))}
                  </div>

                  <div className="flex items-center justify-between">
                    <span className="text-[10px] text-text-muted font-mono">
                      Last seen {formatDistanceToNow(new Date(dev.last_seen), { addSuffix: true })}
                    </span>
                    <NeonButton size="sm" icon={<Terminal size={12} />}>Terminal</NeonButton>
                  </div>
                </div>
              </div>
            </NeonCard>
          ))}
        </div>
      )}
    </div>
  )
}
