import { useState, useEffect } from 'react'
import { getCVContext, type CVContext } from '../api'

const detectors = [
  { id: 'hands', label: 'Hand Tracking', color: '#00d4ff' },
  { id: 'face', label: 'Face Detection', color: '#22c55e' },
  { id: 'pose', label: 'Body Pose', color: '#a855f7' },
  { id: 'objects', label: 'Object Detection', color: '#f59e0b' },
  { id: 'animals', label: 'Animal Detection', color: '#ef4444' },
]

export default function VisionPanel() {
  const [cv, setCV] = useState<CVContext | null>(null)
  const [cameraActive, setCameraActive] = useState(false)
  const [activeDetectors, setActiveDetectors] = useState(detectors.map(d => d.id))

  useEffect(() => {
    const fetchCV = async () => {
      try {
        const ctx = await getCVContext()
        setCV(ctx)
      } catch { /* API may not have CV endpoint yet */ }
    }
    fetchCV()
    const interval = setInterval(fetchCV, 3000)
    return () => clearInterval(interval)
  }, [])

  const toggleDetector = (id: string) => {
    setActiveDetectors(prev =>
      prev.includes(id) ? prev.filter(d => d !== id) : [...prev, id]
    )
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className={`w-3 h-3 rounded-full ${cameraActive ? 'bg-neon-green shadow-[0_0_12px_#22c55e]' : 'bg-neon-red shadow-[0_0_12px_#ef4444]'}`} />
          <span className="text-sm text-text-primary">{cameraActive ? 'Camera Active' : 'Camera Offline'}</span>
        </div>
        <button
          onClick={() => setCameraActive(!cameraActive)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all ${
            cameraActive
              ? 'bg-neon-red/20 text-neon-red border border-neon-red/30'
              : 'bg-cyan-glow/20 text-cyan-glow border border-cyan-glow/30 hover:shadow-[0_0_20px_rgba(0,212,255,0.2)]'
          }`}
        >
          {cameraActive ? 'Stop Camera' : 'Start Camera'}
        </button>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-cyan-glow mb-3">Live Feed</h3>
          <div className="aspect-video bg-black/50 rounded-lg flex items-center justify-center border border-cyan-muted/10">
            {cameraActive ? (
              <div className="text-center">
                <div className="text-4xl mb-2">📷</div>
                <p className="text-sm text-text-muted">Camera feed connected</p>
              </div>
            ) : (
              <div className="text-center">
                <div className="text-4xl mb-2">📷</div>
                <p className="text-sm text-text-muted">Camera offline</p>
                <p className="text-xs text-text-muted mt-1">Start camera to see feed</p>
              </div>
            )}
          </div>
        </div>

        <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
          <h3 className="text-sm font-semibold text-cyan-glow mb-3">Detectors</h3>
          <div className="space-y-2">
            {detectors.map((det) => (
              <button
                key={det.id}
                onClick={() => toggleDetector(det.id)}
                className={`w-full flex items-center justify-between px-3 py-2 rounded-lg transition-all text-sm ${
                  activeDetectors.includes(det.id)
                    ? 'bg-white/5 border border-cyan-muted/20'
                    : 'bg-white/5 opacity-50'
                }`}
              >
                <span className="flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full" style={{ background: det.color, boxShadow: `0 0 8px ${det.color}` }} />
                  {det.label}
                </span>
                <span className={`text-xs ${activeDetectors.includes(det.id) ? 'text-neon-green' : 'text-text-muted'}`}>
                  {activeDetectors.includes(det.id) ? 'ON' : 'OFF'}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-cyan-glow mb-3">Scene Description</h3>
        <div className="bg-black/30 rounded-lg p-4 min-h-[80px]">
          {cv?.description ? (
            <p className="text-sm text-text-primary leading-relaxed">{cv.description}</p>
          ) : (
            <p className="text-sm text-text-muted italic">No scene data available. Start the camera to see detections.</p>
          )}
        </div>
      </div>

      <div className="bg-cyber-dark/60 border border-cyan-muted/20 rounded-xl p-4">
        <h3 className="text-sm font-semibold text-cyan-glow mb-3">Detected Objects</h3>
        <div className="flex flex-wrap gap-2">
          {(cv?.objects ?? []).length > 0 ? (
            cv!.objects.map((obj, i) => (
              <span key={i} className="px-3 py-1.5 rounded-full text-xs font-medium bg-cyan-glow/10 text-cyan-glow border border-cyan-glow/30">
                {obj.label} ({(obj.confidence * 100).toFixed(0)}%)
              </span>
            ))
          ) : (
            <p className="text-sm text-text-muted italic">No objects detected</p>
          )}
        </div>
      </div>
    </div>
  )
}
