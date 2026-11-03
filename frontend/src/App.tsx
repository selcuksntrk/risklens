import { useEffect, useState } from 'react'
import Capture from './Capture'
import Home from './Home'
import Scan from './Scan'
import Replay from './Replay'
import About from './About'

// Hash routes keep the PWA a single static bundle: #/ · #/capture · #/scan/<id>[/v/<id>][/f/<id>] · #/replay/<example> · #/about
function useRoute(): string[] {
  const read = () => location.hash.replace(/^#\/?/, '').split('#')[0].split('/').filter(Boolean)
  const [route, setRoute] = useState(read)
  useEffect(() => {
    // A new screen starts at the top; hash routing would otherwise keep the previous page's scroll offset.
    // In-page anchors (#/about#examples) scroll to their section instead.
    const onChange = () => { setRoute(read()); const anchor = location.hash.split('#')[2]; if (anchor) setTimeout(() => document.getElementById(anchor)?.scrollIntoView(), 50); else window.scrollTo(0, 0) }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}


export default function App() {
  const [page, id, ...rest] = useRoute()
  if (page === 'capture') return <Capture />
  if (page === 'about') return <About />
  if (page === 'verify' && id) return <Capture key={`${id}/${rest[0] ?? ''}`} verifyScanId={id} hazardId={rest[0]} />
  if (page === 'replay' && id) return <Replay key={id} exampleId={id} />
  if (page === 'scan' && id) {
    // #/scan/<id>[/v/<verification>][/f/<finding>]: the finding is a view of the same loaded report, not a new fetch.
    const at = (k: string) => { const i = rest.indexOf(k); return i >= 0 ? rest[i + 1] : undefined }
    const verifyId = at('v')
    return <Scan key={`${id}/${verifyId ?? ''}`} scanId={id} verifyId={verifyId} findingId={at('f')} />
  }
  return <Home />
}
