/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        "surface-dim": "#0c1320",
        "secondary": "#10b981",
        "secondary-fixed": "#4edea3",
        "secondary-container": "#00a572",
        "primary": "#00e5ff",
        "primary-container": "#00e5ff",
        "primary-fixed": "#9cf0ff",
        "tertiary": "#f59e0b",
        "tertiary-container": "#f4cd52",
        "error": "#ef4444",
        "error-container": "#93000a",
        "background": "#070e1b",
        "surface": "#0c1320",
        "surface-container-lowest": "#070e1b",
        "surface-container-low": "#0d1726",
        "surface-container": "#131f33",
        "surface-container-high": "#1a2942",
        "surface-container-highest": "#243754",
        "outline": "#64748b",
        "outline-variant": "#1e293b",
        "on-surface": "#e2e8f0",
        "on-surface-variant": "#94a3b8"
      },
      fontFamily: {
        headline: ["'Space Grotesk'", "sans-serif"],
        body: ["Inter", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
        telemetry: ["'JetBrains Mono'", "monospace"]
      }
    },
  },
  plugins: [],
}
