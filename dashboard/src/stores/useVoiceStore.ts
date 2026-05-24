import { create } from 'zustand'
import type { OrbState } from '../types'

interface VoiceState {
  orbState: OrbState
  transcript: string
  amplitude: number
  isPushToTalk: boolean

  setOrbState: (state: OrbState) => void
  setTranscript: (text: string) => void
  setAmplitude: (val: number) => void
  togglePushToTalk: () => void
}

export const useVoiceStore = create<VoiceState>((set) => ({
  orbState: 'idle',
  transcript: '',
  amplitude: 0,
  isPushToTalk: false,

  setOrbState: (orbState) => set({ orbState }),
  setTranscript: (transcript) => set({ transcript }),
  setAmplitude: (amplitude) => set({ amplitude }),
  togglePushToTalk: () => set((s) => ({ isPushToTalk: !s.isPushToTalk })),
}))
