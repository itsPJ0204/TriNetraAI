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
        sans: ["'Plus Jakarta Sans'", "Inter", "system-ui", "-apple-system", "sans-serif"],
        headline: ["'Plus Jakarta Sans'", "sans-serif"],
        body: ["'Plus Jakarta Sans'", "Inter", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
        telemetry: ["'JetBrains Mono'", "monospace"]
      },
      boxShadow: {
        'glass': '0 8px 32px 0 rgba(0, 0, 0, 0.37)',
        'glass-glow': '0 0 25px -5px rgba(0, 229, 255, 0.25)',
        'glass-card': '0 10px 30px -10px rgba(0, 0, 0, 0.5), inset 0 1px 0 0 rgba(255, 255, 255, 0.08)',
      }
    },
  },
  plugins: [],
}
