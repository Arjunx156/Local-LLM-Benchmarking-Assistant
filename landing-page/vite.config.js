import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          charts: ['recharts'],
          three: ['three', '@react-three/fiber', '@react-three/drei', 'maath'],
          motion: ['framer-motion']
        }
      }
    }
  }
})
