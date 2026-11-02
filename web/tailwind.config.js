/** @type {import('tailwindcss').Config} */
module.exports = {
  darkMode: "class",
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      fontFamily: { sans: ["var(--font-inter)", "system-ui", "sans-serif"] },
      colors: {
        ink: { DEFAULT: "rgb(var(--ink) / <alpha-value>)", soft: "rgb(var(--ink-soft) / <alpha-value>)" },
        surface: { DEFAULT: "rgb(var(--surface) / <alpha-value>)", raised: "rgb(var(--surface-raised) / <alpha-value>)" },
        line: "rgb(var(--line) / <alpha-value>)",
        accent: "rgb(var(--accent) / <alpha-value>)",
      },
    },
  },
  plugins: [],
};
