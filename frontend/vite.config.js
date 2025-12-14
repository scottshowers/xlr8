import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'https://hcmpact-xlr8-production.up.railway.app',
        changeOrigin: true
      },
      '/ws': {
        target: 'wss://hcmpact-xlr8-production.up.railway.app',
        ws: true
      }
    }
  }
})
