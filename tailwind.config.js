/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./templates/**/*.html', './static/**/*.js'],
  prefix: 'tw-',
  corePlugins: { preflight: false },
  theme: { extend: {} },
  plugins: [],
};
