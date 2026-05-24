type SSECallback = (data: string) => void

class SSEManager {
  private connections = new Map<string, EventSource>()

  connect(url: string, onMessage: SSECallback, onError?: () => void): () => void {
    this.disconnect(url)

    const es = new EventSource(url)
    this.connections.set(url, es)

    es.onmessage = (e) => { onMessage(e.data) }
    es.onerror = () => {
      onError?.()
      // EventSource auto-reconnects
    }

    return () => { this.disconnect(url) }
  }

  disconnect(url: string) {
    const es = this.connections.get(url)
    if (es) {
      es.close()
      this.connections.delete(url)
    }
  }

  disconnectAll() {
    this.connections.forEach((es) => es.close())
    this.connections.clear()
  }
}

export const sse = new SSEManager()
