import { motion } from 'framer-motion'
import { useVoiceStore } from '../stores/useVoiceStore'
import clsx from 'clsx'

export function VoicePage() {
  const orbState = useVoiceStore((s) => s.orbState)
  const transcript = useVoiceStore((s) => s.transcript)
  const isPTT = useVoiceStore((s) => s.isPushToTalk)
  const togglePTT = useVoiceStore((s) => s.togglePushToTalk)

  const orbColors: Record<string, string> = { idle: 'bg-gray-600', listening: 'bg-neon-cyan', speaking: 'bg-neon-purple', error: 'bg-neon-red' }

  return (
    <div className="space-y-6">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">Voice Interface</h2>

      {/* Large Orb */}
      <div className="flex flex-col items-center py-6">
        <motion.div
          className={clsx('w-24 h-24 rounded-full cursor-pointer', orbColors[orbState])}
          animate={{
            scale: orbState === 'listening' ? [1, 1.15, 1] : orbState === 'speaking' ? [1, 1.1, 1] : [1, 1.05, 1],
            boxShadow: orbState === 'listening' ? '0 0 40px rgba(0,245,255,0.5)' : orbState === 'speaking' ? '0 0 30px rgba(180,0,255,0.4)' : '0 0 0px transparent',
          }}
          transition={{ duration: orbState === 'idle' ? 2 : 0.6, repeat: Infinity, ease: 'easeInOut' }}
          onClick={() => {
            const isListening = orbState === 'listening'
            fetch(`/api/voice/push-to-talk/${isListening ? 'stop' : 'start'}`, { method: 'POST' }).catch(() => {})
          }}
        />

        {/* Waveform bars */}
        <div className="flex items-center gap-1 mt-4 h-8">
          {[0, 1, 2, 3, 4].map((i) => (
            <motion.div
              key={i}
              className="w-1 rounded-full bg-neon-cyan"
              animate={{
                height: orbState === 'listening' || orbState === 'speaking' ? [8, 24, 12, 20, 8] : 4,
              }}
              transition={{ duration: 0.8, repeat: Infinity, delay: i * 0.1, ease: 'easeInOut' }}
            />
          ))}
        </div>

        <span className="text-xs text-text-dim uppercase tracking-wider mt-2 font-mono">{orbState}</span>
      </div>

      {/* Transcript */}
      <div className="bg-friday-card border border-border-cyan rounded-xl p-4 min-h-32">
        <h3 className="text-xs text-text-dim uppercase tracking-wider mb-2">Transcript</h3>
        <p className="text-sm font-mono text-text-secondary whitespace-pre-wrap">
          {transcript || 'Waiting for voice input…'}
        </p>
      </div>

      {/* PTT toggle */}
      <div className="flex items-center justify-between bg-friday-card border border-border-cyan rounded-xl p-4">
        <div>
          <h4 className="text-sm text-text-primary">Push-to-Talk</h4>
          <p className="text-xs text-text-dim">Hold to speak instead of wake word</p>
        </div>
        <button
          onClick={togglePTT}
          className={clsx('w-10 h-6 rounded-full transition-colors relative', isPTT ? 'bg-neon-cyan' : 'bg-friday-bg-deep border border-border-cyan')}
        >
          <span className={clsx('absolute top-0.5 w-5 h-5 rounded-full bg-white transition-transform', isPTT ? 'left-4.5' : 'left-0.5')} />
        </button>
      </div>
    </div>
  )
}
