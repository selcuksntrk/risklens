// Typed client for the RiskLens API (backend/app/main.py).

export type Severity = 'high' | 'medium' | 'low'

export interface Hazard {
  id: string
  mark: string
  object: string
  relation: string
  severity: Severity
  evidence_frame: string
  rationale: string
  track: string | null
  evidence_image: string
  fix: Fix | null
}

export interface Fix {
  actions: string[]
  fema_sections: { id: string; title: string; pages: string; url: string }[]
  diy: boolean
  cost: string
  minutes: number
  priority: number
}

export interface Report {
  scan_id: string
  created_at: string
  room: { type: string; sleeping_area: boolean; exit_visible: boolean; summary: string; risk_score: number }
  hazards: Hazard[]
  plan: { concepts: { concept: string; alternates: string[]; reason: string }[] }
  objects: Record<string, { concept: string; track: string; frames: number[] }>
  disclaimer: string
  cost_usd: Record<string, number>
  seconds: number
  timings_s?: Record<string, number>
  provenance: {
    source_sha256: string
    models: Record<string, string>
    prompts_sha256: Record<string, string>
    reasoning_summaries: Record<string, string[]>
  }
}

export type Verdict = 'fixed' | 'not_fixed' | 'cannot_verify'

export interface Verification {
  verify_id: string
  created_at: string
  results: Record<string, { verdict: Verdict; confidence: string; what_changed: string; rationale: string;
    object_found: boolean; after_image: string }>
  fixed: number
  risk_score_before: number
  risk_score_after: number
  cost_usd: number
  seconds: number
}

export interface ScanRow { scan_id: string; created_at: string; room: string; risk_score: number; hazards: number }

export interface TimelineEvent { step: string; t: number; [key: string]: unknown }

export type ScanState =
  | { status: 'running' }
  | { status: 'done'; report: Report; fixcards?: string[]; verification?: Verification | null }
  | { status: 'error'; message: string }

// This browser's own scan ids (a per-viewer convenience; the server never lists other people's scans).
const MY_SCANS = 'risklens.scans'
export function myScanIds(): string[] {
  try { return JSON.parse(localStorage.getItem(MY_SCANS) ?? '[]') } catch { return [] }
}
function rememberScan(id: string) {
  try { localStorage.setItem(MY_SCANS, JSON.stringify([id, ...myScanIds()].slice(0, 50))) } catch { /* private mode */ }
}

export async function listScans(): Promise<ScanRow[]> {
  const r = await fetch(`/api/scans?ids=${myScanIds().join(',')}`)
  return r.ok ? r.json() : []
}

export async function getScan(id: string): Promise<ScanState> {
  const r = await fetch(`/api/scans/${id}`)
  if (!r.ok) return { status: 'error', message: `Scan not found (${r.status})` }
  return r.json()
}

export async function uploadScan(video: Blob, filename: string, narration: string): Promise<string> {
  const form = new FormData()
  form.append('video', video, filename)
  form.append('narration', narration)
  const r = await fetch('/api/scans', { method: 'POST', body: form })
  if (!r.ok) {
    const detail = await r.json().then((j) => j.detail).catch(() => r.statusText)
    throw new Error(`Upload failed: ${detail}`)
  }
  const id: string = (await r.json()).scan_id
  rememberScan(id)
  return id
}

export const fileUrl = (scanId: string, path: string) => `/api/scans/${scanId}/files/${path}`

export const RELATION_LABELS: Record<string, string> = {
  above_sleeping_area: 'Can fall on a sleeping area',
  blocks_exit: 'Can block the exit',
  tall_tip_over: 'Can tip over',
  glass_breakage: 'Glass can shatter',
  heavy_falling_object: 'Heavy object can fall',
  other: 'Other hazard',
}

export const ROOM_LABELS: Record<string, string> = {
  bedroom: 'Bedroom', kids_room: "Kids' room", living_room: 'Living room', kitchen: 'Kitchen',
  hallway: 'Hallway', office: 'Office', bathroom: 'Bathroom', other: 'Room',
}

export async function makeFixCard(scanId: string, hazardId: string): Promise<{ image: string; before: string }> {
  const r = await fetch(`/api/scans/${scanId}/hazards/${hazardId}/fixcard`, { method: 'POST' })
  if (!r.ok) {
    const detail = await r.json().then((j) => j.detail).catch(() => r.statusText)
    throw new Error(`Couldn't show the fix: ${detail}`)
  }
  return r.json()
}

export async function uploadVerify(scanId: string, video: Blob, filename: string): Promise<string> {
  const form = new FormData()
  form.append('video', video, filename)
  const r = await fetch(`/api/scans/${scanId}/verify`, { method: 'POST', body: form })
  if (!r.ok) {
    const detail = await r.json().then((j) => j.detail).catch(() => r.statusText)
    throw new Error(`Upload failed: ${detail}`)
  }
  return (await r.json()).verify_id
}
