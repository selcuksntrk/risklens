export type Severity = 'high' | 'medium' | 'low'
export interface Fix {
  actions: string[]
  action_sources: string[][]
  source_status: 'verified' | 'source_unverified' | 'legacy_unknown'
  fema_sections: { id: string; title: string; pages: string; url: string }[]
  diy: boolean; cost: string; minutes: number; priority: number
}
export interface Hazard {
  id: string; mark: string; object: string; relation: string; severity: Severity
  evidence_frame: string; rationale: string; track: string | null; evidence_image: string; fix: Fix | null
  evidence_status: 'observed' | 'needs_check' | 'legacy_unknown'
  evidence_observation: string; next_view_request: string; tracking_supported: boolean; tracking_note?: string
}
export interface Assessment {
  status: 'complete' | 'partial' | 'incomplete' | 'legacy_unknown'
  warnings: string[]; stages?: Record<string, unknown>
}
export interface Report {
  schema_version: number; scan_id: string; created_at: string
  room: { type: string; sleeping_area: boolean; exit_visible: boolean; summary: string; risk_score?: number }
  assessment: Assessment
  context: { occupant_narration: string; source: string }
  hazards: Hazard[]
  plan: { concepts: { concept: string; alternates: string[]; reason: string }[] }
  objects: Record<string, { concept: string; track: string; frames: number[] }>
  disclaimer: string; cost_usd: Record<string, number>; seconds: number; timings_s?: Record<string, number>
  provenance: {
    source_sha256: string; models: Record<string, string | null>; prompts_sha256: Record<string, string>
    reasoning_summaries: Record<string, string[]>; app_version?: string; keyframes?: number[]
  }
}
export type Verdict = 'fixed' | 'not_fixed' | 'cannot_verify'
export interface Verification {
  schema_version?: number; verify_id: string; created_at: string; hazard_id?: string | null
  checked_hazard_ids?: string[]; unchecked_hazard_ids?: string[]
  results: Record<string, { verdict: Verdict; confidence: string; what_changed: string; rationale: string
    object_found: boolean; after_image: string; next_view_request?: string; guard?: string | null }>
  fixed: number; cost_usd: number; seconds: number
}
export interface Counts { high: number; medium: number; low: number; needs_check: number }
export interface ScanRow { scan_id: string; created_at: string; room: string; hazards: number; counts: Counts; assessment_status: string }
export interface Example { id: string; scan_id: string; title: string; description: string; license: string; source_url: string; synthetic: boolean; context?: string }
export interface Attempt { verify_id: string; status: string; created_at: string | null; fixed: number; hazard_id?: string }
export interface TimelineEvent { step: string; t: number; [key: string]: unknown }
export type PartialReport = Pick<Report, 'scan_id' | 'room' | 'hazards' | 'assessment'>
export type ScanState =
  | { status: 'running' | 'queued'; partial?: PartialReport }
  | { status: 'done'; report: Report; fixcards?: string[]; verification?: Verification | null; read_only?: boolean }
  | { status: 'error' | 'interrupted'; message: string; partial?: PartialReport }
export type VerifyState =
  | { status: 'running' | 'queued' }
  | { status: 'done'; verification: Verification }
  | { status: 'error' | 'interrupted'; message: string }

const MY_SCANS = 'risklens.scans'
export function myScanIds(): string[] {
  try { const ids: unknown = JSON.parse(localStorage.getItem(MY_SCANS) ?? '[]'); return Array.isArray(ids) ? ids.filter((x) => typeof x === 'string') : [] } catch { return [] }
}
function rememberScan(id: string) {
  try { localStorage.setItem(MY_SCANS, JSON.stringify([id, ...myScanIds().filter((s) => s !== id)].slice(0, 50))) } catch { /* session still owns the scan */ }
}
export const newUploadKey = () => crypto.randomUUID()
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) { super(message); this.status = status }
}
async function json<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, { credentials: 'same-origin', ...options })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ApiError(response.status, typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`)
  }
  return response.json()
}
let session: Promise<unknown> | null = null
export function ensureSession(): Promise<unknown> {
  if (!session) session = json('/api/session', { method: 'POST' }).catch((e) => { session = null; throw e })
  return session
}
export async function listScans(): Promise<ScanRow[]> {
  await ensureSession()
  return json(`/api/scans?ids=${myScanIds().join(',')}`)
}
export async function getScan(id: string): Promise<ScanState> { return json(`/api/scans/${id}`) }
export async function getVerification(scan: string, id: string): Promise<VerifyState> { return json(`/api/scans/${scan}/verify/${id}`) }
export async function getAttempts(scan: string): Promise<Attempt[]> { return json(`/api/scans/${scan}/verifications`) }
export async function listExamples(): Promise<Example[]> { return json('/api/examples') }
export async function runExample(id: string, key: string): Promise<string> {
  await ensureSession()
  const result = await json<{ scan_id: string }>(`/api/examples/${id}/runs`, { method: 'POST', headers: { 'Idempotency-Key': key } })
  rememberScan(result.scan_id)
  return result.scan_id
}
export async function uploadScan(video: Blob, filename: string, narration: string, key: string): Promise<string> {
  await ensureSession()
  const form = new FormData(); form.append('video', video, filename); form.append('narration', narration)
  const result = await json<{ scan_id: string }>('/api/scans', { method: 'POST', body: form, headers: { 'Idempotency-Key': key } })
  rememberScan(result.scan_id)
  return result.scan_id
}
export async function uploadVerify(scan: string, video: Blob, filename: string, key: string, hazardId?: string): Promise<string> {
  await ensureSession()
  const form = new FormData(); form.append('video', video, filename)
  if (hazardId) form.append('hazard_id', hazardId)
  return (await json<{ verify_id: string }>(`/api/scans/${scan}/verify`, { method: 'POST', body: form, headers: { 'Idempotency-Key': key } })).verify_id
}
export async function deleteScan(id: string): Promise<void> {
  await json(`/api/scans/${id}`, { method: 'DELETE' })
  try { localStorage.setItem(MY_SCANS, JSON.stringify(myScanIds().filter((s) => s !== id))) } catch { /* no cached link */ }
}
export const fileUrl = (scan: string, path: string) => `/api/scans/${scan}/files/${path}`
export async function makeFixCard(scan: string, hazard: string): Promise<{ image: string; before: string }> {
  return json(`/api/scans/${scan}/hazards/${hazard}/fixcard`, { method: 'POST' })
}
export function findingCounts(hazards: Hazard[]): Counts {
  return { high: hazards.filter((h) => h.severity === 'high').length,
    medium: hazards.filter((h) => h.severity === 'medium').length,
    low: hazards.filter((h) => h.severity === 'low').length,
    needs_check: hazards.filter((h) => h.evidence_status !== 'observed').length }
}
export const RELATION_LABELS: Record<string, string> = {
  above_sleeping_area: 'Potential fall onto a sleeping area', blocks_exit: 'Potential obstruction of the exit',
  tall_tip_over: 'Potential tip-over', glass_breakage: 'Glass requires assessment',
  heavy_falling_object: 'Potential falling object', other: 'Other finding',
}
export const ROOM_LABELS: Record<string, string> = {
  bedroom: 'Bedroom', kids_room: "Kids’ room", living_room: 'Living room', kitchen: 'Kitchen',
  hallway: 'Hallway', office: 'Office', bathroom: 'Bathroom', other: 'Room',
}
