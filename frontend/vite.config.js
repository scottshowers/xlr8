import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Debug: Log env vars at build time
console.log('=== VITE BUILD ENV DEBUG ===')
console.log('VITE_SUPABASE_URL exists:', !!process.env.VITE_SUPABASE_URL)
console.log('VITE_SUPABASE_ANON_KEY exists:', !!process.env.VITE_SUPABASE_ANON_KEY)
console.log('All VITE_ vars:', Object.keys(process.env).filter(k => k.startsWith('VITE_')))
console.log('============================')

export default defineConfig({
  plugins: [react()],
  define: {
    // Vercel exposes env vars via process.env at build time
    'import.meta.env.VITE_SUPABASE_URL': JSON.stringify(process.env.VITE_SUPABASE_URL || ''),
    'import.meta.env.VITE_SUPABASE_ANON_KEY': JSON.stringify(process.env.VITE_SUPABASE_ANON_KEY || ''),
    'import.meta.env.VITE_API_URL': JSON.stringify(process.env.VITE_API_URL || ''),
  },
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
