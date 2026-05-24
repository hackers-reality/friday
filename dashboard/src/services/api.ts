import type {
  StatusResponse, Message, Agent, Device, SchedulerJob,
  MemoryChunk, MemoryStats, OsintScanRequest, OsintGraph,
  CameraSnapshot, VisionQueryResult, BrowserState,
  YouTubeStats, YouTubeVideo, YouTubeMetadata,
  TakeoutUpload, PyRunnerScript, PyRunnerSecret,
  AuditEntry, SidecarToken, FridayConfig, LogEntry,
} from '../types'

async function apiFetch<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const r = await fetch(`/api${endpoint}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  })
  if (!r.ok) throw new Error(`API ${r.status}: ${r.statusText}`)
  return r.json() as Promise<T>
}

// ── Status ──
export const getStatus = () => apiFetch<StatusResponse>('/status')

// ── Chat ──
export const sendChat = (message: string) =>
  apiFetch<{ ok: boolean }>('/chat/send', { method: 'POST', body: JSON.stringify({ message }) })
export const getChatHistory = () => apiFetch<Message[]>('/chat/history')

// ── Agents ──
export const getAgents = () => apiFetch<Agent[]>('/agents')
export const dispatchAgent = (agent_id: string, task_type: string, payload: string) =>
  apiFetch<{ task_id: string }>('/agents/spawn', { method: 'POST', body: JSON.stringify({ agent_id, task_type, payload }) })

// ── Devices ──
export const getDevices = () => apiFetch<Device[]>('/devices')

// ── Memory ──
export const searchMemory = (q: string) => apiFetch<MemoryChunk[]>(`/memory/search?q=${encodeURIComponent(q)}`)
export const deleteMemory = (id: string) => apiFetch<{ ok: boolean }>(`/memory/${id}`, { method: 'DELETE' })
export const getMemoryStats = () => apiFetch<MemoryStats>('/memory/status')

// ── OSINT ──
export const launchOsintScan = (req: OsintScanRequest) =>
  apiFetch<{ scan_id: string }>('/osint/scan', { method: 'POST', body: JSON.stringify(req) })
export const getOsintGraph = (id: string) => apiFetch<OsintGraph>(`/osint/graph/${id}`)

// ── Camera / Vision ──
export const getCameraSnapshot = () => apiFetch<CameraSnapshot>('/camera/snapshot')
export const sendVisionQuery = (query: string) =>
  apiFetch<VisionQueryResult>('/vision/query', { method: 'POST', body: JSON.stringify({ query }) })

// ── Browser ──
export const getBrowserState = () => apiFetch<BrowserState>('/browser/state')
export const navigateBrowser = (url: string) =>
  apiFetch<BrowserState>('/browser/navigate', { method: 'POST', body: JSON.stringify({ url }) })
export const browserScreenshot = () => apiFetch<{ image_base64: string }>('/browser/screenshot')

// ── YouTube ──
export const getYoutubeStats = () => apiFetch<YouTubeStats>('/youtube/stats')
export const getYoutubeVideos = () => apiFetch<YouTubeVideo[]>('/youtube/videos')
export const generateYoutubeMetadata = (description: string) =>
  apiFetch<YouTubeMetadata>('/youtube/generate-metadata', { method: 'POST', body: JSON.stringify({ description }) })

// ── Takeout ──
export async function uploadTakeout(file: File): Promise<{ id: string }> {
  const fd = new FormData()
  fd.append('file', file)
  const r = await fetch('/api/takeout/upload', { method: 'POST', body: fd })
  if (!r.ok) throw new Error(`Upload failed: ${r.status}`)
  return r.json()
}
export const getTakeoutHistory = () => apiFetch<TakeoutUpload[]>('/takeout/history')

// ── Scheduler ──
export const getSchedulerJobs = () => apiFetch<SchedulerJob[]>('/scheduler/jobs')
export const toggleJob = (id: string) => apiFetch<{ ok: boolean }>(`/scheduler/${id}/toggle`, { method: 'POST' })
export const runJob = (id: string) => apiFetch<{ ok: boolean }>(`/scheduler/${id}/run`, { method: 'POST' })
export const createJob = (job: Partial<SchedulerJob>) =>
  apiFetch<SchedulerJob>('/scheduler/jobs', { method: 'POST', body: JSON.stringify(job) })
export const deleteJob = (id: string) => apiFetch<{ ok: boolean }>(`/scheduler/${id}`, { method: 'DELETE' })

// ── PyRunner ──
export const getPyRunnerScripts = () => apiFetch<PyRunnerScript[]>('/pyrunner/scripts')
export const saveScript = (id: string, data: Partial<PyRunnerScript>) =>
  apiFetch<PyRunnerScript>(`/pyrunner/scripts/${id}`, { method: 'PUT', body: JSON.stringify(data) })
export const runScript = (id: string) => apiFetch<{ output: string }>(`/pyrunner/scripts/${id}/run`, { method: 'POST' })
export const getSecrets = () => apiFetch<PyRunnerSecret[]>('/pyrunner/secrets')
export const addSecret = (key: string, value: string) =>
  apiFetch<{ ok: boolean }>('/pyrunner/secrets', { method: 'POST', body: JSON.stringify({ key, value }) })
export const deleteSecret = (key: string) => apiFetch<{ ok: boolean }>(`/pyrunner/secrets/${key}`, { method: 'DELETE' })

// ── Settings ──
export const getSettings = () => apiFetch<FridayConfig>('/settings')
export const updateSettings = (config: FridayConfig) =>
  apiFetch<{ ok: boolean }>('/settings', { method: 'PUT', body: JSON.stringify(config) })

// ── Security ──
export const getSecurityAuditLog = () => apiFetch<AuditEntry[]>('/security/audit')
export const getSidecarTokens = () => apiFetch<SidecarToken[]>('/security/tokens')
export const generateSidecarToken = (device_name: string, capabilities: string[]) =>
  apiFetch<{ token: string }>('/security/tokens', { method: 'POST', body: JSON.stringify({ device_name, capabilities }) })
export const revokeSidecarToken = (prefix: string) =>
  apiFetch<{ ok: boolean }>(`/security/tokens/${prefix}`, { method: 'DELETE' })

// ── Logs ──
export const getLogs = () => apiFetch<LogEntry[]>('/logs/recent')

// ── System ──
export const restartFriday = () => apiFetch<{ ok: boolean }>('/system/restart', { method: 'POST' })

// ── Voice ──
export const voicePushToTalkStart = () => apiFetch<{ ok: boolean }>('/voice/push-to-talk/start', { method: 'POST' })
export const voicePushToTalkStop = () => apiFetch<{ ok: boolean }>('/voice/push-to-talk/stop', { method: 'POST' })
