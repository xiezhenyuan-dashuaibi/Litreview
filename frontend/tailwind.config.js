/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: '#2F54EB',
        secondary: '#13C2C2',
        warning: '#FA8C16',
        success: '#52C41A'
      }
    },
  },
  plugins: [],
}