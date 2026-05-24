import type { CameraResultMessage } from '../../../types'

interface Props { message: CameraResultMessage }

export function CameraQueryResult({ message }: Props) {
  return (
    <div className="bg-friday-card border border-border-cyan rounded-xl p-3">
      {message.image_base64 && (
        <img
          src={`data:image/jpeg;base64,${message.image_base64}`}
          alt="Camera capture"
          className="max-h-48 rounded-lg mb-2 w-auto"
        />
      )}
      {message.cv_labels.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mb-2">
          {message.cv_labels.map((lbl, i) => (
            <span
              key={i}
              className="text-[10px] font-mono bg-neon-green/20 text-neon-green px-2 py-0.5 rounded-full"
            >
              {lbl.label} ({(lbl.confidence * 100).toFixed(0)}%)
            </span>
          ))}
        </div>
      )}
      <p className="text-sm text-text-primary">{message.answer}</p>
    </div>
  )
}
