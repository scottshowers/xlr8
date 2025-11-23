import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'https://your-railway-app.up.railway.app',
        changeOrigin: true
      },
      '/ws': {
        target: 'wss://your-railway-app.up.railway.app',
        ws: true
      }
    }
  }
})
