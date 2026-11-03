import { useEffect } from 'react'
import type { Hazard, Severity } from './api'

export function SeverityBadge({ severity }: { severity: Severity }) {
  return <span className={`badge ${severity}`}>{severity} priority</span>
}

export function EvidenceStatus({ status }: { status: Hazard['evidence_status'] }) {
  const text = status === 'observed' ? 'Reported visible' : status === 'needs_check' ? 'Needs checking' : 'Legacy / unknown'
  return <span className={`status ${status}`}>{text}</span>
}

export function Lightbox({ src, alt, onClose }: { src: string; alt: string; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return <div className="lightbox" role="dialog" aria-modal="true" aria-label={alt} onClick={onClose}>
    <img src={src} alt={alt} onClick={(e) => e.stopPropagation()} />
    <button autoFocus onClick={onClose} aria-label="Close image">✕</button>
  </div>
}

export function Logo() {
  return <a className="brand" href="#/"><img src="/favicon.svg" alt="" width={30} height={30} /><strong>RiskLens</strong></a>
}

