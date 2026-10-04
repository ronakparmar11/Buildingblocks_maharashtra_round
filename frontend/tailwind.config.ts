import type { Config } from "tailwindcss";

export default {
  darkMode: "class",
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "var(--color-paper)", panel: "var(--color-panel)", ink: "var(--color-ink)",
        graphite: "var(--color-graphite)", rule: "var(--color-rule)", "rule-soft": "var(--color-rule-soft)",
        orange: "var(--color-orange)", "orange-tint": "var(--color-orange-tint)", warning: "var(--color-warning)",
        caution: "var(--color-caution)", "caution-tint": "var(--color-caution-tint)", normal: "var(--color-normal)",
        "normal-tint": "var(--color-normal-tint)", advisory: "var(--color-advisory)",
        "advisory-tint": "var(--color-advisory-tint)", ghost: "var(--color-ghost)",
        "warning-tint": "var(--color-warning-tint)", "warning-tint-deep": "var(--color-warning-tint-deep)",
        "ink-btn": "var(--color-ink-btn)", "ink-btn-hover": "var(--color-ink-btn-hover)", "ink-btn-active": "var(--color-ink-btn-active)",
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
      boxShadow: { popover: "0 8px 24px var(--shadow-popover, rgba(20,32,43,0.14))" },
    },
  },
  plugins: [],
} satisfies Config;
