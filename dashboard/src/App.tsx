import { useEffect } from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from './components/layout/Layout'
import { ErrorBoundary } from './components/ui/ErrorBoundary'
import { ws } from './services/ws'
import { useSystemStore } from './stores/useSystemStore'
import { useChatStore } from './stores/useChatStore'
import { useVoiceStore } from './stores/useVoiceStore'
import { ChatPage } from './pages/ChatPage'
import { VoicePage } from './pages/VoicePage'
import { AgentsPage } from './pages/AgentsPage'
import { TasksPage } from './pages/TasksPage'
import { OSINTPage } from './pages/OSINTPage'
import { BrowserPage } from './pages/BrowserPage'
import { VisionPage } from './pages/VisionPage'
import { MemoryPage } from './pages/MemoryPage'
import { YoutubePage } from './pages/YoutubePage'
import { TakeoutPage } from './pages/TakeoutPage'
import { AnalyticsPage } from './pages/AnalyticsPage'
import { DevicesPage } from './pages/DevicesPage'
import { SchedulerPage } from './pages/SchedulerPage'
import { PyRunnerPage } from './pages/PyRunnerPage'
import { SecurityPage } from './pages/SecurityPage'
import { LogsPage } from './pages/LogsPage'
import { SettingsPage } from './pages/SettingsPage'

export function App() {
  const fetchStatus = useSystemStore((s) => s.fetchStatus)
  const setConnected = useSystemStore((s) => s.setConnected)
  const addAlert = useSystemStore((s) => s.addAlert)
  const pushLog = useSystemStore((s) => s.pushLog)
  const updateAgent = useSystemStore((s) => s.updateAgent)
  const addMessage = useChatStore((s) => s.addMessage)
  const appendToken = useChatStore((s) => s.appendToken)
  const finalizeStream = useChatStore((s) => s.finalizeStream)
  const setOrbState = useVoiceStore((s) => s.setOrbState)
  const setTranscript = useVoiceStore((s) => s.setTranscript)

  useEffect(() => {
    ws.connect()
    fetchStatus()

    const unsubs = [
      ws.on('_connection', (msg) => {
        const p = msg.payload as { connected?: boolean }
        setConnected(Boolean(p?.connected))
      }),
      ws.on('status', () => { fetchStatus() }),
      ws.on('log', (msg) => {
        if (msg.payload) pushLog(msg.payload as import('./types').LogEntry)
      }),
      ws.on('alert', (msg) => {
        if (msg.payload) addAlert(msg.payload as import('./types').Alert)
      }),
      ws.on('chat.token', (msg) => {
        const p = msg.payload as { token?: string }
        if (p?.token) appendToken(p.token)
      }),
      ws.on('chat.complete', (msg) => {
        finalizeStream()
        if (msg.payload) addMessage(msg.payload as import('./types').Message)
      }),
      ws.on('agent.status', (msg) => {
        if (msg.payload) updateAgent(msg.payload as import('./types').Agent)
      }),
      ws.on('voice.state', (msg) => {
        const p = msg.payload as { state?: import('./types').OrbState }
        if (p?.state) setOrbState(p.state)
      }),
      ws.on('voice.transcript', (msg) => {
        const p = msg.payload as { text?: string }
        if (p?.text) setTranscript(p.text)
      }),
    ]

    const poll = setInterval(fetchStatus, 15000)

    return () => {
      unsubs.forEach((u) => u())
      clearInterval(poll)
      ws.disconnect()
    }
  }, [])

  return (
    <ErrorBoundary>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<ChatPage />} />
          <Route path="/voice" element={<VoicePage />} />
          <Route path="/agents" element={<AgentsPage />} />
          <Route path="/tasks" element={<TasksPage />} />
          <Route path="/osint" element={<OSINTPage />} />
          <Route path="/browser" element={<BrowserPage />} />
          <Route path="/vision" element={<VisionPage />} />
          <Route path="/memory" element={<MemoryPage />} />
          <Route path="/youtube" element={<YoutubePage />} />
          <Route path="/takeout" element={<TakeoutPage />} />
          <Route path="/analytics" element={<AnalyticsPage />} />
          <Route path="/devices" element={<DevicesPage />} />
          <Route path="/scheduler" element={<SchedulerPage />} />
          <Route path="/pyrunner" element={<PyRunnerPage />} />
          <Route path="/security" element={<SecurityPage />} />
          <Route path="/logs" element={<LogsPage />} />
          <Route path="/settings" element={<SettingsPage />} />
        </Route>
      </Routes>
    </ErrorBoundary>
  )
}
