import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./app/**/*.{ts,tsx,mdx}",
    "./components/**/*.{ts,tsx,mdx}",
    "./lib/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        // Paleta MudAção
        mudacao: {
          50: "#f0f7f4",
          100: "#dbeee4",
          200: "#b8dcc8",
          300: "#8dc3a5",
          400: "#5ea27f",
          500: "#3d8861",
          600: "#2c6c4c",
          700: "#22553d",
          800: "#1a4231",
          900: "#0a4a3a", // primário
          950: "#062920",
        },
      },
      fontFamily: {
        sans: ["-apple-system", "BlinkMacSystemFont", "Segoe UI", "sans-serif"],
      },
    },
  },
  plugins: [],
};

export default config;
