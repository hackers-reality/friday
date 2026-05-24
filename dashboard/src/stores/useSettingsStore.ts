import { create } from 'zustand'
import type { FridayConfig } from '../types'

interface SettingsState {
  config: FridayConfig | null
  isDirty: boolean
  activeTab: string

  fetchConfig: () => Promise<void>
  updateSetting: (section: string, key: string, value: unknown) => void
  setActiveTab: (tab: string) => void
  resetDirty: () => void
  saveConfig: () => Promise<void>
}

export const useSettingsStore = create<SettingsState>((set, get) => ({
  config: null,
  isDirty: false,
  activeTab: 'general',

  fetchConfig: async () => {
    try {
      const r = await fetch('/api/settings')
      if (!r.ok) return
      const data = (await r.json()) as FridayConfig
      set({ config: data, isDirty: false })
    } catch { /* offline */ }
  },

  updateSetting: (section, key, value) => {
    const cfg = get().config
    if (!cfg) return
    const updated = { ...cfg, [section]: { ...(cfg as Record<string, Record<string, unknown>>)[section], [key]: value } }
    set({ config: updated as FridayConfig, isDirty: true })
  },

  setActiveTab: (activeTab) => set({ activeTab }),
  resetDirty: () => set({ isDirty: false }),

  saveConfig: async () => {
    const cfg = get().config
    if (!cfg) return
    try {
      await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(cfg),
      })
      set({ isDirty: false })
    } catch { /* offline */ }
  },
}))
