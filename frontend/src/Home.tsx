import { useEffect, useState } from 'react'
import { go } from './App'
import { listScans, ROOM_LABELS, type ScanRow } from './api'
import { riskBand } from './Scan'

export default function Home() {
  const [scans, setScans] = useState<ScanRow[]>([])
  useEffect(() => { listScans().then(setScans) }, [])

  return (
    <main className="page">
      <header className="brand">
        <img src="/favicon.svg" alt="" width={36} height={36} />
        <h1>RiskLens</h1>
      </header>
      <section className="hero">
        <h2>Most earthquake injuries come from what's inside the home.</h2>
        <p>Film a room for a minute. RiskLens finds what can fall, tip, shatter or block your way out, and shows you how to fix it.</p>
        <button className="primary big" onClick={() => go('capture')}>Scan a room</button>
        <p className="fine">Non-structural hazards only. RiskLens does not assess the building's structure.</p>
      </section>
      {scans.length > 0 && (
        <section>
          <h3>Your scans</h3>
          <ul className="scan-list">
            {scans.map((s) => {
              const band = riskBand(s.risk_score)
              return (
                <li key={s.scan_id}>
                  <button className="row" onClick={() => go(`scan/${s.scan_id}`)}>
                    <span className={`score ${band.cls}`}>{s.risk_score}</span>
                    <span className="grow">
                      <strong>{ROOM_LABELS[s.room] ?? s.room}</strong>
                      <small>{s.hazards} hazard{s.hazards === 1 ? '' : 's'} · {new Date(s.created_at).toLocaleString()}</small>
                    </span>
                    <span aria-hidden>›</span>
                  </button>
                </li>
              )
            })}
          </ul>
        </section>
      )}
    </main>
  )
}
