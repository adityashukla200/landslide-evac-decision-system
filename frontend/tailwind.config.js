/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        // Mission Control & Emergency Semantic Colors
        brand: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          600: '#0284c7',
          700: '#0369a1',
          900: '#0c4a6e',
          950: '#082f49',
        },
        emergency: {
          safe: '#10b981',      // Green - Safe / Normal
          watch: '#f59e0b',     // Amber - Advisory / Watch
          warning: '#f97316',   // Orange - Warning / Prepare
          evacuate: '#ef4444',  // Red - Evacuate Immediately
          critical: '#b91c1c',  // Dark Crimson - Extreme Life Threat
          degraded: '#64748b',  // Slate - Degraded / Offline
          fault: '#a855f7',     // Purple - Sensor Anomaly
        },
        surface: {
          DEFAULT: '#0b0f19',
          subtle: '#111827',
          card: '#182234',
          border: '#1e293b',
          hover: '#24334a',
        }
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'monospace'],
      },
      animation: {
        'pulse-subtle': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'pulse-fast': 'pulse 1s cubic-bezier(0.4, 0, 0.6, 1) infinite',
      }
    },
  },
  plugins: [],
}
