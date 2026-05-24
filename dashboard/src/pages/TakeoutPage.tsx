import { useCallback } from 'react'
import { useDropzone } from 'react-dropzone'
import { EmptyState } from '../components/ui/EmptyState'
import { Upload } from 'lucide-react'

export function TakeoutPage() {
  const onDrop = useCallback((files: File[]) => {
    files.forEach((file) => {
      const fd = new FormData()
      fd.append('file', file)
      fetch('/api/takeout/upload', { method: 'POST', body: fd }).catch(() => {})
    })
  }, [])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({ onDrop, accept: { 'application/zip': ['.zip'] } })

  return (
    <div className="space-y-4">
      <h2 className="text-sm font-display text-neon-cyan tracking-wider">Google Takeout</h2>

      {/* Dropzone */}
      <div
        {...getRootProps()}
        className={`border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors ${
          isDragActive ? 'border-neon-cyan bg-neon-cyan/5' : 'border-border-cyan hover:border-neon-cyan/40'
        }`}
      >
        <input {...getInputProps()} />
        <Upload size={32} className="text-text-dim mx-auto mb-3" />
        <p className="text-sm text-text-secondary">
          {isDragActive ? 'Drop the ZIP file here…' : 'Drop Google Takeout ZIP here or click to browse'}
        </p>
        <p className="text-[10px] text-text-muted mt-1">Supports .zip files</p>
      </div>

      {/* Upload History placeholder */}
      <EmptyState icon="📦" title="No Uploads" description="Upload a Google Takeout archive to analyze your data" />
    </div>
  )
}
