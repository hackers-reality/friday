// ─── Core Types ─────────────────────────────────────────────

export type OrbState = 'idle' | 'listening' | 'speaking' | 'error';
export type AlertSeverity = 'info' | 'warn' | 'error' | 'critical';
export type AgentStatus = 'idle' | 'running' | 'completed' | 'failed' | 'offline';
export type DeviceStatus = 'online' | 'offline';
export type JobStatus = 'active' | 'paused' | 'failed';
export type TaskState = 'queued' | 'running' | 'done' | 'failed';

// ─── Messages ───────────────────────────────────────────────

export interface BaseMessage {
  id: string;
  timestamp: string;
}

export interface UserMessage extends BaseMessage {
  type: 'user';
  content: string;
  voice_input?: boolean;
  attachments?: FileAttachment[];
}

export interface FridayMessage extends BaseMessage {
  type: 'friday';
  content: string;
  isStreaming?: boolean;
}

export interface AgentResultMessage extends BaseMessage {
  type: 'agent_result';
  agent_name: string;
  agent_id: string;
  model: string;
  task_type: string;
  content: string;
  duration_ms: number;
  status: 'completed' | 'failed';
}

export interface OsintResultMessage extends BaseMessage {
  type: 'osint_result';
  target: string;
  platforms_found: number;
  threats: number;
  entities: number;
  graph_id: string;
}

export interface SystemMessage extends BaseMessage {
  type: 'system';
  content: string;
}

export interface BriefingMessage extends BaseMessage {
  type: 'briefing';
  sections: BriefingSection[];
  date: string;
}

export interface CameraResultMessage extends BaseMessage {
  type: 'camera_result';
  image_base64: string;
  cv_labels: CVLabel[];
  answer: string;
}

export type Message =
  | UserMessage
  | FridayMessage
  | AgentResultMessage
  | OsintResultMessage
  | SystemMessage
  | BriefingMessage
  | CameraResultMessage;

// ─── Briefing ───────────────────────────────────────────────

export interface BriefingSection {
  title: string;
  content: string;
  collapsed?: boolean;
}

export interface BriefingData {
  sections: BriefingSection[];
  date: string;
  ready: boolean;
}

// ─── File Attachments ───────────────────────────────────────

export interface FileAttachment {
  id: string;
  name: string;
  type: string;
  size: number;
  preview?: string;
  data?: File;
}

// ─── Agents ─────────────────────────────────────────────────

export interface Agent {
  id: string;
  name: string;
  display_name: string;
  model: string;
  task_types: string[];
  status: AgentStatus;
  current_task?: string;
  success_rate: number;
  tasks_today: number;
  enabled: boolean;
  progress?: number;
  current_action?: string;
}

export interface AgentDispatchRequest {
  agent_id: string;
  task_type: string;
  payload: string;
}

// ─── Devices ────────────────────────────────────────────────

export interface Device {
  name: string;
  platform: 'windows' | 'macos' | 'linux' | 'android' | 'ios';
  status: DeviceStatus;
  capabilities: string[];
  telemetry: DeviceTelemetry;
  last_seen: string;
}

export interface DeviceTelemetry {
  cpu: number;
  ram: number;
  disk: number;
  battery?: number;
}

// ─── Tasks ──────────────────────────────────────────────────

export interface Task {
  id: string;
  agent_id: string;
  agent_name: string;
  task_type: string;
  state: TaskState;
  payload: string;
  result?: string;
  started_at: string;
  duration_ms?: number;
}

// ─── Jobs (Scheduler) ───────────────────────────────────────

export interface SchedulerJob {
  id: string;
  name: string;
  schedule: string;
  schedule_type: 'cron' | 'interval';
  next_run: string;
  last_run?: string;
  status: JobStatus;
  target: string;
  description?: string;
}

// ─── OSINT ──────────────────────────────────────────────────

export interface OsintScanRequest {
  target: string;
  target_type: 'username' | 'email' | 'ip' | 'domain' | 'image';
  tools: string[];
}

export interface OsintEntity {
  id: string;
  type: 'PERSON' | 'IP' | 'DOMAIN' | 'EMAIL' | 'LOCATION' | 'DEVICE' | 'ACCOUNT';
  label: string;
  attributes: Record<string, string>;
}

export interface OsintEdge {
  source: string;
  target: string;
  label: string;
}

export interface OsintGraph {
  nodes: OsintEntity[];
  edges: OsintEdge[];
}

// ─── Memory ─────────────────────────────────────────────────

export interface MemoryChunk {
  id: string;
  content: string;
  category: string;
  source: string;
  metadata: Record<string, string>;
  distance?: number;
  created_at: string;
  pinned?: boolean;
}

export interface MemoryStats {
  total_chunks: number;
  by_category: Record<string, number>;
  by_source: Record<string, number>;
}

// ─── YouTube ────────────────────────────────────────────────

export interface YouTubeStats {
  subscribers: number;
  subscribers_delta: number;
  views: number;
  views_delta: number;
  videos: number;
  quota_used: number;
  quota_limit: number;
}

export interface YouTubeVideo {
  video_id: string;
  title: string;
  views: number;
  likes: number;
  comments: number;
  published_at: string;
}

export interface ContentIdea {
  id: string;
  idea: string;
  reasoning: string;
  score: number;
  used: boolean;
}

export interface YouTubeMetadata {
  title: string;
  description: string;
  tags: string[];
  chapters: { time: string; title: string }[];
}

// ─── Vision / Camera ────────────────────────────────────────

export interface CVLabel {
  label: string;
  type: 'face' | 'hand' | 'object';
  confidence: number;
  bbox: [number, number, number, number];
}

export interface CameraSnapshot {
  image_base64: string;
  cv_labels: CVLabel[];
  timestamp: string;
}

export interface VisionQueryResult {
  answer: string;
  image_base64: string;
  cv_labels: CVLabel[];
}

// ─── Browser ────────────────────────────────────────────────

export interface BrowserState {
  url: string;
  title: string;
  screenshot_base64?: string;
  is_loading: boolean;
  session: string;
}

// ─── Takeout ────────────────────────────────────────────────

export interface TakeoutProgress {
  service: string;
  progress: number;
  total: number;
  status: 'pending' | 'processing' | 'done' | 'error';
}

export interface TakeoutUpload {
  id: string;
  filename: string;
  uploaded_at: string;
  services: string[];
  status: 'processing' | 'done' | 'error';
}

// ─── PyRunner ───────────────────────────────────────────────

export interface PyRunnerScript {
  id: string;
  name: string;
  code: string;
  schedule?: string;
  packages: string[];
  last_run?: string;
  last_status?: 'success' | 'error';
  created_at: string;
}

export interface PyRunnerSecret {
  key: string;
  created_at: string;
}

// ─── Security ───────────────────────────────────────────────

export interface AuditEntry {
  id: string;
  timestamp: string;
  action: string;
  source: string;
  details: string;
  severity: AlertSeverity;
}

export interface SidecarToken {
  device_name: string;
  token_prefix: string;
  capabilities: string[];
  created_at: string;
  last_used?: string;
}

// ─── Alerts ─────────────────────────────────────────────────

export interface Alert {
  id: string;
  severity: AlertSeverity;
  source: string;
  message: string;
  timestamp: string;
  dismissed?: boolean;
}

// ─── Logs ───────────────────────────────────────────────────

export interface LogEntry {
  timestamp: string;
  level: 'DEBUG' | 'INFO' | 'WARN' | 'ERROR';
  module: string;
  message: string;
  stack_trace?: string;
}

// ─── System Status ──────────────────────────────────────────

export interface SystemStatus {
  version: string;
  uptime: number;
  cpu: number;
  memory: number;
  disk: number;
  agents_active: number;
  devices_online: number;
  memory_chunks: number;
  connected: boolean;
}

// ─── Settings ───────────────────────────────────────────────

export interface FridayConfig {
  general: {
    name: string;
    version: string;
    model: string;
    voice_enabled: boolean;
  };
  voice: {
    wake_word: string;
    voice_name: string;
    input_device?: string;
    sensitivity: number;
  };
  agents: {
    max_parallel: number;
    default_timeout_ms: number;
    auto_retry: boolean;
  };
  camera: {
    enabled: boolean;
    device_index: number;
    fps: number;
    cv_pipeline: boolean;
  };
  browser: {
    backend: 'playwright' | 'pyppeteer' | 'auto';
    headless: boolean;
    profile_path?: string;
  };
  memory: {
    auto_store: boolean;
    vector_db_path: string;
    max_chunks: number;
  };
  notifications: {
    desktop: boolean;
    telegram: boolean;
    discord: boolean;
    webhook_url?: string;
  };
}

// ─── WebSocket Messages ─────────────────────────────────────

export interface WSMessage {
  type: string;
  payload: unknown;
  timestamp?: string;
}

// ─── API Response Wrappers ──────────────────────────────────

export interface ApiResponse<T> {
  ok: boolean;
  data: T;
  error?: string;
}

export interface StatusResponse {
  brain: {
    model: string;
    version: string;
    uptime: number;
  };
  agents: Agent[];
  devices: Device[];
  youtube?: YouTubeStats;
  memory: { chunks: number };
  scheduler: { jobs: SchedulerJob[] };
}
