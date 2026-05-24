import { Modal } from './Modal'
import { NeonButton } from './NeonButton'

interface ConfirmDialogProps {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  message: string
  confirmText?: string
  variant?: 'danger' | 'warning'
}

export function ConfirmDialog({ isOpen, onClose, onConfirm, title, message, confirmText = 'Confirm', variant = 'danger' }: ConfirmDialogProps) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <p className="text-sm text-text-secondary mb-4">{message}</p>
      <div className="flex justify-end gap-3 pt-3 border-t border-border-cyan">
        <NeonButton variant="secondary" size="sm" onClick={onClose}>Cancel</NeonButton>
        <NeonButton variant={variant === 'danger' ? 'danger' : 'primary'} size="sm" onClick={() => { onConfirm(); onClose() }}>
          {confirmText}
        </NeonButton>
      </div>
    </Modal>
  )
}
