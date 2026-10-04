import { useEffect, useRef } from "react";

const BAYER = [
  [0, 32, 8, 40, 2, 34, 10, 42],
  [48, 16, 56, 24, 50, 18, 58, 26],
  [12, 44, 4, 36, 14, 46, 6, 38],
  [60, 28, 52, 20, 62, 30, 54, 22],
  [3, 35, 11, 43, 1, 33, 9, 41],
  [51, 19, 59, 27, 49, 17, 57, 25],
  [15, 47, 7, 39, 13, 45, 5, 37],
  [63, 31, 55, 23, 61, 29, 53, 21],
];

function hex(h: string): [number, number, number] {
  const n = parseInt(h.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

export default function DitherWave({
  className = "",
  primaryColor = "#FF4F00",
  secondaryColor = "#FF8C42",
  tertiaryColor = "#14202B",
  speed = 1,
  intensity = 1,
  scale = 6,
}: {
  className?: string;
  primaryColor?: string;
  secondaryColor?: string;
  tertiaryColor?: string;
  speed?: number;
  intensity?: number;
  scale?: number;
}) {
  const ref = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const c = ref.current;
    if (!c) return;
    const ctx = c.getContext("2d", { alpha: false });
    if (!ctx) return;

    let raf = 0;
    const cA = hex(primaryColor);
    const cB = hex(secondaryColor);
    const cC = hex(tertiaryColor);

    const resize = () => {
      const r = c.getBoundingClientRect();
      c.width = Math.ceil(r.width / 2);
      c.height = Math.ceil(r.height / 2);
    };

    const draw = (t: number) => {
      const w = c.width;
      const h = c.height;
      if (!w || !h) { raf = requestAnimationFrame(draw); return; }

      const img = ctx.createImageData(w, h);
      const d = img.data;
      const time = t * 0.0004 * speed;
      const s = scale * 0.7;

      for (let y = 0; y < h; y++) {
        const ny = y / h;
        for (let x = 0; x < w; x++) {
          const nx = x / w;

          const d1 = Math.sin(nx * s + ny * s * 0.6 + time) * 0.5;
          const d2 = Math.sin(ny * s * 1.3 - nx * s * 0.4 + time * 0.7) * 0.4;
          const d3 = Math.sin((nx - 0.5) * s * 2 + time * 0.5) * 0.3;
          const d4 = Math.cos(ny * s * 0.8 + nx * s * 0.3 - time * 0.9) * 0.25;
          const radial = 1.0 - Math.hypot(nx - 0.5, ny - 0.45) * 0.8;

          let v = (d1 + d2 + d3 + d4) * intensity * 0.5 + radial * 0.4 + 0.35;
          v = v < 0 ? 0 : v > 1 ? 1 : v;

          // smooth 3-stop gradient
          let r: number, g: number, b: number;
          if (v < 0.45) {
            const t2 = v / 0.45;
            const ease = t2 * t2 * (3 - 2 * t2);
            r = cC[0] + (cA[0] - cC[0]) * ease;
            g = cC[1] + (cA[1] - cC[1]) * ease;
            b = cC[2] + (cA[2] - cC[2]) * ease;
          } else {
            const t2 = (v - 0.45) / 0.55;
            const ease = t2 * t2 * (3 - 2 * t2);
            r = cA[0] + (cB[0] - cA[0]) * ease;
            g = cA[1] + (cB[1] - cA[1]) * ease;
            b = cA[2] + (cB[2] - cA[2]) * ease;
          }

          // ordered dithering: quantize to 8 levels per channel
          const threshold = (BAYER[y & 7][x & 7] + 0.5) / 64;
          const q = 8;
          const dr = (r / 255) * (q - 1);
          const dg = (g / 255) * (q - 1);
          const db = (b / 255) * (q - 1);

          const i = (y * w + x) << 2;
          d[i]     = ((dr + threshold | 0) / (q - 1)) * 255;
          d[i + 1] = ((dg + threshold | 0) / (q - 1)) * 255;
          d[i + 2] = ((db + threshold | 0) / (q - 1)) * 255;
          d[i + 3] = 255;
        }
      }

      ctx.putImageData(img, 0, 0);
      raf = requestAnimationFrame(draw);
    };

    resize();
    raf = requestAnimationFrame(draw);
    window.addEventListener("resize", resize);

    const mq = window.matchMedia("(prefers-reduced-motion: reduce)");
    if (mq.matches) { cancelAnimationFrame(raf); draw(0); }

    return () => { cancelAnimationFrame(raf); window.removeEventListener("resize", resize); };
  }, [primaryColor, secondaryColor, tertiaryColor, speed, intensity, scale]);

  return (
    <canvas
      ref={ref}
      aria-hidden="true"
      className={`pointer-events-none ${className}`}
      style={{ imageRendering: "pixelated" }}
    />
  );
}
