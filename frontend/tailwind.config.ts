import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        background: "#0B0B0C",
        surface: "#141416",
        border: "#26262A",
        foreground: "#E8E8EA",
        muted: "#8A8A92",
        brand: "#FF6B00",
        pass: "#22C55E",
        fail: "#EF4444",
        reused: "#3F3F46",
        changed: "#F59E0B",
      },
      fontFamily: {
        sans: ["Inter", "sans-serif"],
        mono: ["JetBrains Mono", "monospace"],
      },
    },
  },
  plugins: [],
} satisfies Config;
