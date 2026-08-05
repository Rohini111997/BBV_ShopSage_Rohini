import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      // Override when the backend isn't on 8000, e.g.
      //   VITE_API_TARGET=http://127.0.0.1:8001 npm run dev
      '/api': process.env.VITE_API_TARGET || 'http://127.0.0.1:8000',
    },
  },
})
