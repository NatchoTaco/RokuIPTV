import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        forge: {
          50: "#eef8ff",
          100: "#d9efff",
          300: "#7cc7f3",
          500: "#2494c7",
          700: "#17627f",
          900: "#102f3b",
        },
        ember: {
          400: "#f59e63",
          500: "#ea7b43",
        },
      },
      boxShadow: {
        panel: "0 18px 60px rgba(0, 0, 0, 0.24)",
      },
    },
  },
  plugins: [],
} satisfies Config;
