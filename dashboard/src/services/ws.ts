import type { WSMessage } from '../types'

type Listener = (msg: WSMessage) => void

class WSClient {
  private socket: WebSocket | null = null
  private listeners = new Map<string, Set<Listener>>()
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null
  private url = ''
  isConnected = false

  connect(url?: string) {
    this.url = url ?? `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws`
    this._doConnect()
  }

  private _doConnect() {
    try {
      this.socket = new WebSocket(this.url)

      this.socket.onopen = () => {
        this.isConnected = true
        this._emit('_connection', { type: '_connection', payload: { connected: true } })
      }

      this.socket.onmessage = (e) => {
        try {
          const msg = JSON.parse(String(e.data)) as WSMessage
          this._emit(msg.type, msg)
          this._emit('*', msg)
        } catch { /* bad json */ }
      }

      this.socket.onclose = () => {
        this.isConnected = false
        this._emit('_connection', { type: '_connection', payload: { connected: false } })
        this._scheduleReconnect()
      }

      this.socket.onerror = () => {
        this.socket?.close()
      }
    } catch {
      this._scheduleReconnect()
    }
  }

  private _scheduleReconnect() {
    if (this.reconnectTimer) return
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null
      this._doConnect()
    }, 3000)
  }

  disconnect() {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer)
      this.reconnectTimer = null
    }
    this.socket?.close()
    this.socket = null
    this.isConnected = false
  }

  send(data: Record<string, unknown>) {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(data))
    }
  }

  on(type: string, callback: Listener): () => void {
    if (!this.listeners.has(type)) this.listeners.set(type, new Set())
    this.listeners.get(type)!.add(callback)
    return () => { this.listeners.get(type)?.delete(callback) }
  }

  private _emit(type: string, msg: WSMessage) {
    this.listeners.get(type)?.forEach((fn) => {
      try { fn(msg) } catch { /* listener error */ }
    })
  }
}

export const ws = new WSClient()
