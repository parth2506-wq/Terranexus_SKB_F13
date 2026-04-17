/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        earth: {
          50:  '#f5f9f0',
          100: '#e8f2de',
          200: '#cde4b8',
          300: '#a9cf89',
          400: '#7fb558',
          500: '#5c9934',
          600: '#467a27',
          700: '#386020',
          800: '#2e4d1c',
          900: '#264019',
        },
        sky: {
          50:  '#f0f7ff',
          100: '#e0effe',
          200: '#bae0fd',
          300: '#7cc8fb',
          400: '#36aaf5',
          500: '#0c8fe6',
          600: '#0071c4',
          700: '#015a9e',
          800: '#064d83',
          900: '#0b406d',
        },
        amber: {
          50:  '#fffbeb',
          100: '#fef3c7',
          200: '#fde68a',
          300: '#fcd34d',
          400: '#fbbf24',
          500: '#f59e0b',
          600: '#d97706',
          700: '#b45309',
          800: '#92400e',
          900: '#78350f',
        },
        carbon: {
          50:  '#f8f9fa',
          100: '#f1f3f5',
          200: '#e9ecef',
          300: '#dee2e6',
          400: '#ced4da',
          500: '#adb5bd',
          600: '#6c757d',
          700: '#495057',
          800: '#343a40',
          900: '#212529',
        }
      },
      fontFamily: {
        display: ['"DM Serif Display"', 'Georgia', 'serif'],
        body: ['"DM Sans"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      backdropBlur: {
        xs: '2px',
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(31, 38, 135, 0.08)',
        'glass-lg': '0 16px 48px 0 rgba(31, 38, 135, 0.12)',
        'card': '0 2px 12px rgba(0,0,0,0.06), 0 1px 3px rgba(0,0,0,0.04)',
        'card-hover': '0 8px 24px rgba(0,0,0,0.10), 0 2px 6px rgba(0,0,0,0.06)',
      },
      animation: {
        'pulse-slow': 'pulse 3s cubic-bezier(0.4, 0, 0.6, 1) infinite',
        'fade-in': 'fadeIn 0.5s ease-out',
        'slide-up': 'slideUp 0.4s ease-out',
      },
      keyframes: {
        fadeIn: { '0%': { opacity: 0 }, '100%': { opacity: 1 } },
        slideUp: { '0%': { opacity: 0, transform: 'translateY(16px)' }, '100%': { opacity: 1, transform: 'translateY(0)' } },
      }
    },
  },
  plugins: [],
}
