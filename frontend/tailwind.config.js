/** @type {import('tailwindcss').Config} */
import forms from '@tailwindcss/forms';
import containerQueries from '@tailwindcss/container-queries';

export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "on-secondary-fixed": "#131c29",
        "on-surface": "#1a1c1e",
        "on-tertiary-container": "#b5785f",
        "tertiary-container": "#391303",
        "on-tertiary-fixed": "#351002",
        "primary-fixed-dim": "#afc8f0",
        "inverse-on-surface": "#f2f0f3",
        "outline": "#74777f",
        "secondary": "#565f6e",
        "on-error-container": "#93000a",
        "surface-dim": "#dbd9dd",
        "error": "#ba1a1a",
        "on-primary-fixed": "#001c3a",
        "surface": "#faf9fc",
        "inverse-surface": "#2f3033",
        "tertiary-fixed-dim": "#fdb69a",
        "surface-container-highest": "#e3e2e5",
        "on-background": "#1a1c1e",
        "on-tertiary-fixed-variant": "#6b3a25",
        "secondary-fixed": "#dae3f5",
        "secondary-fixed-dim": "#bec7d9",
        "surface-container-high": "#e9e7eb",
        "on-tertiary": "#ffffff",
        "secondary-container": "#d7e0f2",
        "surface-bright": "#faf9fc",
        "tertiary-fixed": "#ffdbce",
        "surface-container-lowest": "#ffffff",
        "on-secondary-container": "#5a6372",
        "on-error": "#ffffff",
        "on-secondary": "#ffffff",
        "background": "#faf9fc",
        "on-primary-container": "#6f88ad",
        "surface-container-low": "#f4f3f6",
        "inverse-primary": "#afc8f0",
        "surface-container": "#efedf0",
        "primary": "#000613",
        "on-primary": "#ffffff",
        "tertiary": "#110200",
        "primary-container": "#001f3f",
        "primary-fixed": "#d4e3ff",
        "outline-variant": "#c4c6cf",
        "surface-tint": "#476083",
        "on-primary-fixed-variant": "#2f486a",
        "on-secondary-fixed-variant": "#3e4756",
        "error-container": "#ffdad6",
        "on-surface-variant": "#43474e",
        "surface-variant": "#e3e2e5"
      },
      fontFamily: {
        headline: ["Manrope", "sans-serif"],
        body: ["Inter", "sans-serif"],
        label: ["Inter", "sans-serif"]
      },
      borderRadius: {
        "DEFAULT": "0.125rem",
        "lg": "0.25rem",
        "xl": "0.5rem",
        "full": "0.75rem"
      }
    },
  },
  plugins: [forms, containerQueries],
}
