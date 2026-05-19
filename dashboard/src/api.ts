const API_BASE = 'http://127.0.0.1:8090/api';

export async function fetchJson<T>(endpoint: string): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`);
  if (!res.ok) throw new Error(`API error: ${res.status}`);
  return res.json();
}

export const getHealth = () => fetchJson<Health>('/health');
export const getSystem = () => fetchJson<SystemInfo>('/system');
export const getMemoryStatus = () => fetchJson<MemoryStatus>('/memory/status');
export const getTools = () => fetchJson<ToolCall[]>('/tools');
export const getSidecars = () => fetchJson<Sidecar[]>('/sidecars');
export const getSnapshots = () => fetchJson<Snapshot[]>('/snapshots');
export const getDiagnostic = () => fetchJson<Diagnostic>('/diagnostic');
export const getCVContext = () => fetchJson<CVContext>('/cv');

export interface Health {
  status: string;
  uptime: number;
  version: string;
}

export interface SystemInfo {
  cpu: number;
  ram: number;
  disk: number;
  modules: ModuleStatus[];
}

export interface ModuleStatus {
  name: string;
  loaded: boolean;
}

export interface MemoryStatus {
  name: string;
  version: string;
  conversations_audited: number;
  last_updated: string;
  categories: { name: string; confidence: number }[];
}

export interface ToolCall {
  tool: string;
  timestamp: string;
  status: string;
}

export interface Sidecar {
  name: string;
  host: string;
  status: string;
  last_heartbeat: string;
  capabilities: string[];
}

export interface Snapshot {
  id: string;
  timestamp: string;
  summary: string;
}

export interface Diagnostic {
  status: string;
  issues: string[];
  doctor_ok: boolean;
  logs: LogEntry[];
}

export interface LogEntry {
  level: string;
  message: string;
  timestamp: string;
}

export interface CVContext {
  objects: DetectedObject[];
  description: string;
}

export interface DetectedObject {
  label: string;
  confidence: number;
  bbox: [number, number, number, number];
}
