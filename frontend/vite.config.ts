import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// SPA dev server proxies API + static-font requests to the FastAPI backend.
// Production: `npm run build` -> dist/, served by FastAPI (see server/app.py).
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/ask': 'http://127.0.0.1:8000',
      '/examples': 'http://127.0.0.1:8000',
      '/health': 'http://127.0.0.1:8000',
    },
  },
})
