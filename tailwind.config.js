/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './templates/**/*.html',
    './**/templates/**/*.html',
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['"Google Sans"', 'Roboto', 'Arial', 'sans-serif'],
      },
      colors: {
        ai: {
          bg: '#131314',
          surface: '#1e1f20',
          surface2: '#282a2c',
          border: '#3c4043',
          text: '#e8eaed',
          muted: '#9aa0a6',
          blue: '#8ab4f8',
          primary: '#a8c7fa',
        },
      },
    },
  },
  plugins: [],
}
