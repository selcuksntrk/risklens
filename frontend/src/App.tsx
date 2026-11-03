import { useEffect, useState } from 'react'
import Capture from './Capture'
import Home from './Home'
import Scan from './Scan'
import Replay from './Replay'

// Hash routes keep the PWA a single static bundle: #/ · #/capture · #/scan/<id> · #/replay/<example>
function useRoute(): string[] {
  const read = () => location.hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  const [route, setRoute] = useState(read)
  useEffect(() => {
    // A new screen starts at the top; hash routing would otherwise keep the previous page's scroll offset.
    const onChange = () => { setRoute(read()); window.scrollTo(0, 0) }
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}


export default function App() {
  const [page, id, sub, subId] = useRoute()
  if (page === 'capture') return <Capture />
  if (page === 'verify' && id) return <Capture key={`${id}/${sub ?? ''}`} verifyScanId={id} hazardId={sub} />
  if (page === 'replay' && id) return <Replay key={id} exampleId={id} />
  if (page === 'scan' && id) return <Scan key={`${id}/${subId ?? ''}`} scanId={id} verifyId={sub === 'v' ? subId : undefined} />
  return <Home />
}
