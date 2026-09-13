/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        navy: {
          50: '#eef4fb',
          100: '#d9e6f6',
          200: '#b3cbed',
          300: '#7fa9de',
          400: '#4c86cb',
          500: '#2a69b0',
          600: '#1f5390',
          700: '#1a4273',
          800: '#16355c',
          900: '#122948',
          950: '#0b1b32',
        },
        brand: {
          orange: '#F7941D',
          'orange-dark': '#e07f0a',
          blue: '#1B62B5',
          'blue-dark': '#0e3f7e',
          green: '#39B54A',
        },
      },
      fontFamily: {
        sans: ['Noto Sans Gujarati', 'Inter', 'system-ui', 'sans-serif'],
      },
      boxShadow: {
        card: '0 2px 12px rgba(18, 41, 72, 0.08)',
        'card-hover': '0 6px 24px rgba(18, 41, 72, 0.14)',
      },
    },
  },
  plugins: [],
}
