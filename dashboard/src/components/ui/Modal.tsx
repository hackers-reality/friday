import { useEffect, type ReactNode } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { X } from 'lucide-react'
import clsx from 'clsx'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: ReactNode
  size?: 'sm' | 'md' | 'lg'
}

const sizeMap = { sm: 'max-w-sm', md: 'max-w-lg', lg: 'max-w-2xl' }

export function Modal({ isOpen, onClose, title, children, size = 'md' }: ModalProps) {
  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    if (isOpen) document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
          />
          <motion.div
            className={clsx('fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full z-50 bg-friday-card border border-border-cyan rounded-2xl shadow-2xl', sizeMap[size])}
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.15 }}
          >
            <div className="flex items-center justify-between p-4 border-b border-border-cyan">
              <h3 className="text-sm font-display text-neon-cyan tracking-wider">{title}</h3>
              <button onClick={onClose} className="text-text-dim hover:text-text-primary transition-colors">
                <X size={16} />
              </button>
            </div>
            <div className="p-4 overflow-y-auto max-h-[70vh]">{children}</div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  )
}
