import { StrictMode, Suspense, lazy } from 'react'
import { createRoot } from 'react-dom/client'
import { HashRouter } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import './index.css'

const App = lazy(() => import('./App').then((m) => ({ default: m.App })))

function LoadingScreen() {
  return (
    <div className="h-screen flex items-center justify-center bg-friday-bg">
      <div className="text-center">
        <div className="text-5xl mb-4 animate-pulse-glow">🛸</div>
        <div className="text-xs text-text-dim uppercase tracking-[0.3em] font-mono">
          Initializing FRIDAY…
        </div>
      </div>
    </div>
  )
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <HashRouter>
      <Suspense fallback={<LoadingScreen />}>
        <App />
      </Suspense>
      <Toaster
        position="bottom-right"
        toastOptions={{
          style: {
            background: '#0d0d1a',
            color: '#ddddee',
            border: '1px solid rgba(0,245,255,0.12)',
            borderRadius: '10px',
            fontSize: '13px',
            fontFamily: "'DM Sans', sans-serif",
          },
        }}
      />
    </HashRouter>
  </StrictMode>,
)
