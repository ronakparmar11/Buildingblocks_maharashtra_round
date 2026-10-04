function v(name: string, fallback: string) {
  if (typeof document === "undefined") return fallback;
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim() || fallback;
}

export const CHART = {
  get orange() { return v("--chart-orange", "#FF4F00"); },
  get ink() { return v("--chart-ink", "#14202B"); },
  get graphite() { return v("--chart-graphite", "#5B6873"); },
  get rule() { return v("--chart-rule", "#DFE5E8"); },
  get ruleHard() { return v("--chart-rule-hard", "#C9D2D8"); },
  get advisory() { return v("--chart-advisory", "#0B6E8A"); },
  get caution() { return v("--chart-caution", "#D48A00"); },
  get panel() { return v("--color-panel", "#FBFCFC"); },
} as const;
