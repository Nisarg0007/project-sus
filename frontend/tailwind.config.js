/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        'sus': {
          'bg': '#080B12',
          'bg-alt': '#0D111A',
          'surface': '#111827',
          'surface-light': '#1f2937',
          'border': '#1a1f2e',
          'text': '#F3F4F6',
          'text-dim': '#8A94A6',
          'cyan': '#38BDF8',
          'blue': '#3b82f6',
          'green': '#34D399',
          'amber': '#FBBF24',
          'red': '#FF5C5C',
        },
      },
      fontFamily: {
        sans: ['Inter', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
      fontSize: {
        'display': ['4rem', { lineHeight: '1.1', letterSpacing: '-0.02em' }],
        'hero': ['3rem', { lineHeight: '1.2', letterSpacing: '-0.01em' }],
      },
    },
  },
  plugins: [],
}
