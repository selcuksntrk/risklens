import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev: the API runs on :8000 (uvicorn). In production FastAPI serves the built app from the same origin.
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    allowedHosts: true,
    proxy: {
      '/api': { target: 'http://localhost:8000', ws: true },
    },
  },
})
