import type { Config } from "tailwindcss";

export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#EEF1F2", panel: "#FBFCFC", ink: "#14202B",
        graphite: "#5B6873", rule: "#C9D2D8", "rule-soft": "#DFE5E8",
        orange: "#FF4F00", "orange-tint": "#FFE4D6", warning: "#C8223A",
        caution: "#D48A00", "caution-tint": "#FBEFD5", normal: "#1E8A4C",
        "normal-tint": "#DDF1E5", advisory: "#0B6E8A", ghost: "#AEB8BF",
      },
      fontFamily: {
        sans: ["Archivo", "Segoe UI", "system-ui", "sans-serif"],
        mono: ["B612 Mono", "ui-monospace", "Consolas", "monospace"],
      },
      fontSize: {
        xs: ["12px", "16px"], sm: ["14px", "20px"], md: ["16px", "24px"],
        lg: ["20px", "28px"], xl: ["25px", "32px"], "2xl": ["31px", "38px"],
        "3xl": ["39px", "44px"],
      },
      borderRadius: { chip: "999px", control: "6px", panel: "10px", node: "8px" },
      boxShadow: { popover: "0 8px 24px rgba(20,32,43,0.14)" },
    },
  },
  plugins: [],
} satisfies Config;
