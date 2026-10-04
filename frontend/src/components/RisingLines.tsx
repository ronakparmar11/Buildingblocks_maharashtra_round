import { useEffect, useRef } from "react";

function hexRgb(hex: string): string {
  const n = parseInt(hex.slice(1), 16);
  return `${(n >> 16) & 255},${(n >> 8) & 255},${n & 255}`;
}

export default function RisingLines({
  className = "",
  color = "#FF4F00",
  haloColor = "#FF8C42",
  horizonColor = "#FF4F00",
}: {
  className?: string;
  color?: string;
  haloColor?: string;
  horizonColor?: string;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext("2d")!;
    if (!ctx) return;

    let raf = 0;
    let w = 0;
    let h = 0;
    let dpr = 1;
    const cMain = hexRgb(color);
    const cHalo = hexRgb(haloColor);
    const cHorizon = hexRgb(horizonColor);

    const LINES = Array.from({ length: 10 }, (_, i) => ({
      xPct: 0.08 + (i / 10) * 0.84 + (Math.random() - 0.5) * 0.05,
      width: 1 + Math.random() * 1.5,
      haloWidth: 20 + Math.random() * 30,
      speed: 0.6 + Math.random() * 0.8,
      phase: Math.random() * Math.PI * 2,
      drift: 0.3 + Math.random() * 0.4,
      opacity: 0.5 + Math.random() * 0.5,
    }));

    const PARTICLES = Array.from({ length: 50 }, () => ({
      x: Math.random(),
      y: Math.random(),
      speed: 0.0008 + Math.random() * 0.0015,
      size: 1.5 + Math.random() * 2.5,
      glow: 8 + Math.random() * 16,
      opacity: 0.4 + Math.random() * 0.6,
      lineIdx: Math.floor(Math.random() * 10),
      drift: (Math.random() - 0.5) * 0.03,
    }));

    const resize = () => {
      dpr = Math.min(window.devicePixelRatio, 2);
      const rect = c.getBoundingClientRect();
      w = rect.width;
      h = rect.height;
      c.width = w * dpr;
      c.height = h * dpr;
      c.style.width = `${w}px`;
      c.style.height = `${h}px`;
    };

    const draw = (t: number) => {
      const time = t * 0.001;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);

      // horizon glow
      const hg = ctx.createRadialGradient(w * 0.5, h * 1.05, 0, w * 0.5, h * 1.05, w * 0.6);
      hg.addColorStop(0, `rgba(${cHorizon},0.35)`);
      hg.addColorStop(0.4, `rgba(${cHorizon},0.1)`);
      hg.addColorStop(1, `rgba(${cHorizon},0)`);
      ctx.fillStyle = hg;
      ctx.fillRect(0, 0, w, h);

      // additive blending for all light elements
      ctx.globalCompositeOperation = "lighter";

      // draw beams
      for (const line of LINES) {
        const baseX = line.xPct * w;
        const sway = Math.sin(time * line.speed + line.phase) * line.drift * 40;
        const x = baseX + sway;

        // wide halo glow
        const haloGrad = ctx.createLinearGradient(0, h, 0, 0);
        haloGrad.addColorStop(0, `rgba(${cHalo},${0.08 * line.opacity})`);
        haloGrad.addColorStop(0.3, `rgba(${cHalo},${0.04 * line.opacity})`);
        haloGrad.addColorStop(0.8, `rgba(${cHalo},0)`);

        ctx.beginPath();
        ctx.moveTo(x - line.haloWidth / 2, h);
        ctx.quadraticCurveTo(x + sway * 0.3, h * 0.4, x + sway * 0.5, 0);
        ctx.quadraticCurveTo(x + sway * 0.3 + line.haloWidth, h * 0.4, x + line.haloWidth / 2, h);
        ctx.closePath();
        ctx.fillStyle = haloGrad;
        ctx.fill();

        // core beam
        const shimmer = 0.6 + 0.4 * Math.sin(time * 3 + line.phase);
        const coreGrad = ctx.createLinearGradient(0, h, 0, 0);
        coreGrad.addColorStop(0, `rgba(${cMain},${0.7 * line.opacity * shimmer})`);
        coreGrad.addColorStop(0.2, `rgba(${cMain},${0.5 * line.opacity * shimmer})`);
        coreGrad.addColorStop(0.7, `rgba(${cMain},${0.15 * line.opacity * shimmer})`);
        coreGrad.addColorStop(1, `rgba(${cMain},0)`);

        ctx.beginPath();
        ctx.moveTo(x, h);
        ctx.quadraticCurveTo(x + sway * 0.3, h * 0.4, x + sway * 0.5, 0);
        ctx.strokeStyle = coreGrad;
        ctx.lineWidth = line.width;
        ctx.stroke();

        // bright center with glow
        ctx.save();
        ctx.shadowColor = `rgba(${cMain},0.8)`;
        ctx.shadowBlur = 6;
        ctx.beginPath();
        ctx.moveTo(x, h);
        ctx.quadraticCurveTo(x + sway * 0.3, h * 0.4, x + sway * 0.5, 0);
        ctx.strokeStyle = `rgba(255,255,255,${0.15 * line.opacity * shimmer})`;
        ctx.lineWidth = line.width * 0.5;
        ctx.stroke();
        ctx.restore();
      }

      // rising particles
      for (const p of PARTICLES) {
        p.y -= p.speed;
        if (p.y < -0.05) {
          p.y = 1.05;
          p.x = LINES[p.lineIdx].xPct + (Math.random() - 0.5) * 0.04;
        }

        const line = LINES[p.lineIdx];
        const sway = Math.sin(time * line.speed + line.phase) * line.drift * 40;
        const progress = 1 - p.y;
        const px = (p.x + p.drift * Math.sin(time * 2 + p.y * 6)) * w + sway * progress;
        const py = p.y * h;

        const fade = Math.sin(p.y * Math.PI);

        // particle glow
        ctx.save();
        ctx.shadowColor = `rgba(${cMain},0.9)`;
        ctx.shadowBlur = p.glow;
        ctx.beginPath();
        ctx.arc(px, py, p.size, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(${cMain},${p.opacity * fade})`;
        ctx.fill();
        ctx.restore();

        // bright core
        ctx.beginPath();
        ctx.arc(px, py, p.size * 0.4, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(255,255,255,${0.6 * p.opacity * fade})`;
        ctx.fill();
      }

      ctx.globalCompositeOperation = "source-over";

      // top and side vignette
      const vig = ctx.createRadialGradient(w * 0.5, h * 0.6, h * 0.3, w * 0.5, h * 0.6, w * 0.9);
      vig.addColorStop(0, "rgba(13,17,23,0)");
      vig.addColorStop(1, "rgba(13,17,23,0.7)");
      ctx.fillStyle = vig;
      ctx.fillRect(0, 0, w, h);

      raf = requestAnimationFrame(draw);
    };

    resize();
    raf = requestAnimationFrame(draw);
    window.addEventListener("resize", resize);

    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) { cancelAnimationFrame(raf); draw(0); }

    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, [color, haloColor, horizonColor]);

  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      className={`pointer-events-none ${className}`}
    />
  );
}
