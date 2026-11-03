export const MODELS = {
  spark: 'Muse Spark 1.3',
  sam: 'SAM 3.1',
  image: 'Muse Image 1.0',
}

/** The five stages of a scan, shared by the live stage, the replay and the "how it was made" panel. */
export const STAGES = [
  { key: 'ingest', label: 'Prepare', model: 'Video → keyframes' },
  { key: 'planner', label: 'Plan', model: MODELS.spark },
  { key: 'sam', label: 'Track', model: MODELS.sam },
  { key: 'surveyor', label: 'Survey', model: MODELS.spark },
  { key: 'fixer', label: 'Next steps', model: `${MODELS.spark} + FEMA E-74` },
] as const

export const fmtSeconds = (s?: number | null) => s === undefined || s === null ? '' : s >= 60 ? `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, '0')}` : `${Math.round(s)} s`
