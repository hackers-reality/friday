import { create } from 'zustand'
import type { Agent, Device, Alert, Task, LogEntry, SystemStatus, StatusResponse } from '../types'

interface SystemState {
  agents: Agent[]
  devices: Device[]
  alerts: Alert[]
  systemStatus: SystemStatus | null
  activeJobs: Task[]
  logs: LogEntry[]
  connected: boolean
  sidebarCollapsed: boolean
  fetchStatus: () => Promise<void>
  dismissAlert: (id: string) => void
  addAlert: (alert: Alert) => void
  updateAgent: (agent: Agent) => void
  setConnected: (val: boolean) => void
  setStatus: (data: StatusResponse) => void
  pushLog: (entry: LogEntry) => void
  toggleSidebar: () => void
}

export const useSystemStore = create<SystemState>((set, get) => ({
  agents: [],
  devices: [],
  alerts: [],
  systemStatus: null,
  activeJobs: [],
  logs: [],
  connected: false,
  sidebarCollapsed: false,

  fetchStatus: async () => {
    try {
      const r = await fetch('/api/status')
      if (!r.ok) return
      const data = (await r.json()) as StatusResponse
      get().setStatus(data)
    } catch {
      /* offline */
    }
  },

  dismissAlert: (id) =>
    set((s) => ({ alerts: s.alerts.filter((a) => a.id !== id) })),

  addAlert: (alert) =>
    set((s) => ({ alerts: [alert, ...s.alerts].slice(0, 50) })),

  updateAgent: (agent) =>
    set((s) => ({
      agents: s.agents.map((a) => (a.id === agent.id ? agent : a)),
    })),

  setConnected: (connected) => set({ connected }),

  setStatus: (data) =>
    set({
      agents: data.agents ?? [],
      devices: data.devices ?? [],
      systemStatus: {
        version: data.brain?.version ?? '2.0.0',
        uptime: data.brain?.uptime ?? 0,
        cpu: 0,
        memory: 0,
        disk: 0,
        agents_active: (data.agents ?? []).filter((a) => a.status === 'running').length,
        devices_online: (data.devices ?? []).filter((d) => d.status === 'online').length,
        memory_chunks: data.memory?.chunks ?? 0,
        connected: true,
      },
      connected: true,
    }),

  pushLog: (entry) =>
    set((s) => ({ logs: [...s.logs, entry].slice(-500) })),

  toggleSidebar: () =>
    set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),
}))
