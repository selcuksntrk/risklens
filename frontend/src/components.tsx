import { useEffect, type ReactNode } from 'react'
import type { Severity } from './api'
import { RELATION_LABELS } from './api'
import { PRIORITY } from './ui'

export function Logo() {
  return <a className="brand" href="#/"><span className="brand-mark" aria-hidden />RiskLens</a>
}

export function Top({ children }: { children?: ReactNode }) {
  return <header className="top"><Logo />{children ?? <nav aria-label="Main"><a href="#/about">How it works</a></nav>}</header>
}

export function Back({ to, label }: { to: string; label: string }) {
  return <a className="back" href={`#/${to}`}>‹ {label}</a>
}

/** "● High priority · could tip over" */
export function Severity({ severity, relation }: { severity: Severity; relation?: string }) {
  return <span className={`sev ${severity}`}>{PRIORITY[severity]}{relation && <span>· {RELATION_LABELS[relation] ?? relation}</span>}</span>
}

export function Fold({ title, children, open = false }: { title: ReactNode; children: ReactNode; open?: boolean }) {
  return <details className="fold" open={open}><summary>{title}</summary><div>{children}</div></details>
}

export function Lightbox({ src, alt, onClose }: { src: string; alt: string; onClose: () => void }) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])
  return <div className="lightbox" role="dialog" aria-modal="true" aria-label={alt} onClick={onClose}>
    <img src={src} alt={alt} onClick={(e) => e.stopPropagation()} />
    <button autoFocus onClick={onClose} aria-label="Close">✕</button>
  </div>
}

/** The one-line reminder every result screen carries, with the details one tap away. */
export function Limits() {
  return <p className="fine">A visual check by AI models, not a building inspection. Hidden fixings can't be seen in a video. <a href="#/about">How it works and its limits</a></p>
}
