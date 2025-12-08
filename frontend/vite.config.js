import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig(({ mode }) => {
  // Load env variables
  const env = loadEnv(mode, process.cwd(), '')
  
  return {
    plugins: [react()],
    define: {
      // Explicitly expose VITE_ prefixed env vars
      'import.meta.env.VITE_SUPABASE_URL': JSON.stringify(env.VITE_SUPABASE_URL),
      'import.meta.env.VITE_SUPABASE_ANON_KEY': JSON.stringify(env.VITE_SUPABASE_ANON_KEY),
      'import.meta.env.VITE_API_URL': JSON.stringify(env.VITE_API_URL || ''),
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
  }
})
