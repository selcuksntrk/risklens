import type { Hazard } from './api'

export const MODELS = {
  spark: 'Muse Spark 1.3',
  sam: 'SAM 3.1',
  image: 'Muse Image 1.0',
}

/** The stages of a scan in plain words, shared by the live progress, the replay and "how this report was made". */
export const STAGES = [
  { key: 'ingest', label: 'Getting your video ready', model: 'picks still frames from the video' },
  { key: 'planner', label: 'Deciding what to look at', model: MODELS.spark },
  { key: 'sam', label: 'Following each object through the video', model: MODELS.sam },
  { key: 'surveyor', label: 'Checking what could fall, tip or block the way', model: MODELS.spark },
  { key: 'fixer', label: 'Writing next steps from FEMA guidance', model: `${MODELS.spark} + FEMA E-74` },
] as const

export const PRIORITY = { high: 'High priority', medium: 'Medium priority', low: 'Low priority' } as const

export const fmtSeconds = (s?: number | null) => s === undefined || s === null ? '' : s >= 60 ? `${Math.floor(s / 60)} min ${Math.round(s % 60)} s` : `${Math.round(s)} s`

const ORDER = { high: 0, medium: 1, low: 2 }
export const sortFindings = (hazards: Hazard[]) => [...hazards].sort((a, b) => ORDER[a.severity] - ORDER[b.severity])
export const findingHref = (scanId: string, hazardId: string, verifyId?: string) => `#/scan/${scanId}${verifyId ? `/v/${verifyId}` : ''}/f/${hazardId}`
export const VERDICT_WORD = { fixed: 'Change visible', not_fixed: 'Looks the same', cannot_verify: 'Can’t tell from this video' }


/** Model-written object names arrive in lower case ("white tall wardrobe"); show them as titles. */
export const cap = (s: string) => s ? s.charAt(0).toUpperCase() + s.slice(1) : s
