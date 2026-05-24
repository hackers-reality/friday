import { Component, type ReactNode, type ErrorInfo } from 'react'

interface Props { children: ReactNode }
interface State { hasError: boolean; error: Error | null }

export class ErrorBoundary extends Component<Props, State> {
  state: State = { hasError: false, error: null }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen flex items-center justify-center bg-friday-bg p-8">
          <div className="bg-friday-card border border-neon-red/30 rounded-2xl p-8 max-w-md text-center">
            <span className="text-4xl mb-4 block">⚠️</span>
            <h2 className="text-lg font-display text-neon-red tracking-wider mb-2">System Error</h2>
            <p className="text-sm text-text-secondary mb-4">
              {this.state.error?.message ?? 'Something went wrong'}
            </p>
            <button
              onClick={() => { this.setState({ hasError: false, error: null }); window.location.reload() }}
              className="text-sm bg-neon-red/20 border border-neon-red/30 text-neon-red px-4 py-2 rounded-lg hover:bg-neon-red/30 transition-colors"
            >
              Reload Dashboard
            </button>
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
