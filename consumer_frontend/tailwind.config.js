/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: '#4A90E2', // Soft blue
          light: '#7DB3F5',
          dark: '#2E5F9E'
        },
        accent: {
          DEFAULT: '#A8D5F2', // Light blue
          light: '#C9E4F9',
          dark: '#6FB8E8'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        display: ['Poppins', 'system-ui', 'sans-serif']
      }
    },
  },
  plugins: [],
}
