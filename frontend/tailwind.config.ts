import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}", "./lib/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        maroon: { 50: "#fbf3f4", 100: "#f5e1e4", 200: "#e8bcc3", 500: "#8a2a3b", 600: "#6e1f2e", 700: "#5a1825", 800: "#3f111a", 900: "#2a0b11" },
        gold: { 50: "#fdf8ec", 100: "#f8ecc9", 300: "#ecc86f", 400: "#e3b54a", 500: "#c99a2e", 600: "#a47a1f" },
        ink: "#1c1917",
      },
      fontFamily: { sans: ["ui-sans-serif", "system-ui", "-apple-system", "Segoe UI", "Roboto", "Noto Sans Devanagari", "Mangal", "sans-serif"], display: ["Georgia", "Cambria", "Noto Serif Devanagari", "serif"] },
    },
  },
  plugins: [],
};
export default config;
