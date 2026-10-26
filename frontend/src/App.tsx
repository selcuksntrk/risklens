import { useEffect, useState } from 'react'
import Capture from './Capture'
import Home from './Home'
import Scan from './Scan'

// Hash routes keep the PWA a single static bundle: #/ · #/capture · #/scan/<id>
function useRoute(): string[] {
  const read = () => location.hash.replace(/^#\/?/, '').split('/').filter(Boolean)
  const [route, setRoute] = useState(read)
  useEffect(() => {
    const onChange = () => setRoute(read())
    window.addEventListener('hashchange', onChange)
    return () => window.removeEventListener('hashchange', onChange)
  }, [])
  return route
}

export const go = (path: string) => { location.hash = `#/${path}` }

export default function App() {
  const [page, id] = useRoute()
  if (page === 'capture') return <Capture />
  if (page === 'scan' && id) return <Scan scanId={id} />
  return <Home />
}
