export const go = (path: string) => { location.hash = `#/${path}` }

export const VIDEO_ACCEPT = 'video/mp4,video/quicktime,video/webm,.mov,.mp4,.webm'

// A file chosen on the home screen is handed to the capture screen, which owns validation and upload.
let pending: File | null = null
export function startUpload(file: File) { pending = file; go('capture') }
export function takePendingUpload(): File | null { const f = pending; pending = null; return f }
