"use client";

import { useEffect, useRef } from "react";

const COUNT = 120;
const LINK_DISTANCE = 145;
const MAX_SPEED = 0.32;
const NODE_RADIUS = 2;
const PULSE_NODE_RATIO = 0.16;
const WAVE_POINTS = 72;
const WAVE_AMPLITUDE = 26;
const WAVE_DRIFT_SPEED = 0.007;

type Tone = "cool" | "warm" | "neutral";

type Node = {
  x: number;
  y: number;
  vx: number;
  vy: number;
  tone: Tone;
  pulse: boolean;
  phase: number;
};

// All-cool palette — three blues so the mesh reads as a unified high-tech
// network rather than a multi-hue scatter.
//   cyan-300   = sky-cyan      (cool / lightest)
//   sky-400    = bright sky    (warm-slot — now also cool)
//   blue-400   = mid blue      (neutral)
const COLORS: Record<Tone, [number, number, number]> = {
  cool: [103, 232, 249],     // cyan-300
  warm: [56, 189, 248],      // sky-400
  neutral: [96, 165, 250],   // blue-400
};

function pickTone(i: number): Tone {
  const r = i % 10;
  if (r < 3) return "cool";
  if (r < 6) return "warm";
  return "neutral";
}

export function AnimatedBackground() {
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext("2d", { alpha: true });
    if (!ctx) return;

    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    let width = 0;
    let height = 0;
    let nodes: Node[] = [];
    let raf = 0;
    let alive = true;
    let frame = 0;

    const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      width = rect.width;
      height = rect.height;
      canvas.width = Math.floor(width * dpr);
      canvas.height = Math.floor(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };

    const seed = () => {
      nodes = [];
      const pulseEvery = Math.max(1, Math.floor(1 / PULSE_NODE_RATIO));
      for (let i = 0; i < COUNT; i++) {
        nodes.push({
          x: Math.random() * width,
          y: Math.random() * height,
          vx: (Math.random() - 0.5) * MAX_SPEED * 2,
          vy: (Math.random() - 0.5) * MAX_SPEED * 2,
          tone: pickTone(i),
          pulse: i % pulseEvery === 0,
          phase: Math.random() * Math.PI * 2,
        });
      }
    };

    const linkColor = (a: Tone, b: Tone, alpha: number) => {
      const c = a === b ? COLORS[a] : COLORS.neutral;
      return `rgba(${c[0]}, ${c[1]}, ${c[2]}, ${alpha})`;
    };

    const drawWave = () => {
      const y0 = height - 60;
      const step = width / (WAVE_POINTS - 1);
      ctx.beginPath();
      for (let i = 0; i < WAVE_POINTS; i++) {
        const x = i * step;
        const t = frame * WAVE_DRIFT_SPEED + i * 0.35;
        const y =
          y0 +
          Math.sin(t) * WAVE_AMPLITUDE * 0.6 +
          Math.sin(t * 1.7) * WAVE_AMPLITUDE * 0.4;
        if (i === 0) ctx.moveTo(x, y);
        else ctx.lineTo(x, y);
      }
      ctx.strokeStyle = "rgba(103, 232, 249, 0.38)"; // cyan-300, slightly brighter
      ctx.lineWidth = 1.4;
      ctx.stroke();
    };

    const draw = () => {
      ctx.clearRect(0, 0, width, height);
      drawWave();

      if (!reducedMotion) {
        for (const n of nodes) {
          n.x += n.vx;
          n.y += n.vy;
          if (n.x < 0 || n.x > width) n.vx *= -1;
          if (n.y < 0 || n.y > height) n.vy *= -1;
          n.x = Math.max(0, Math.min(width, n.x));
          n.y = Math.max(0, Math.min(height, n.y));
        }
      }

      for (let i = 0; i < nodes.length; i++) {
        const a = nodes[i];
        for (let j = i + 1; j < nodes.length; j++) {
          const b = nodes[j];
          const dx = a.x - b.x;
          const dy = a.y - b.y;
          const d2 = dx * dx + dy * dy;
          if (d2 > LINK_DISTANCE * LINK_DISTANCE) continue;
          const t = 1 - Math.sqrt(d2) / LINK_DISTANCE;
          ctx.strokeStyle = linkColor(a.tone, b.tone, t * 0.45);
          ctx.lineWidth = 1;
          ctx.beginPath();
          ctx.moveTo(a.x, a.y);
          ctx.lineTo(b.x, b.y);
          ctx.stroke();
        }
      }

      for (const n of nodes) {
        const [r, g, b] = COLORS[n.tone];
        let radius = NODE_RADIUS;
        let alpha = 0.88;

        if (n.pulse) {
          const phase = reducedMotion ? 0 : frame * 0.04 + n.phase;
          const pulse = 0.5 + 0.5 * Math.sin(phase);
          radius = NODE_RADIUS + pulse * 1.6;
          alpha = 0.7 + pulse * 0.3;

          const grad = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, radius * 5);
          grad.addColorStop(0, `rgba(${r}, ${g}, ${b}, ${0.32 * pulse})`);
          grad.addColorStop(1, `rgba(${r}, ${g}, ${b}, 0)`);
          ctx.fillStyle = grad;
          ctx.beginPath();
          ctx.arc(n.x, n.y, radius * 5, 0, Math.PI * 2);
          ctx.fill();
        }

        ctx.fillStyle = `rgba(${r}, ${g}, ${b}, ${alpha})`;
        ctx.beginPath();
        ctx.arc(n.x, n.y, radius, 0, Math.PI * 2);
        ctx.fill();
      }

      frame += 1;
      if (alive && !reducedMotion) {
        raf = requestAnimationFrame(draw);
      }
    };

    resize();
    seed();
    draw();

    const onResize = () => {
      resize();
      seed();
    };
    window.addEventListener("resize", onResize);

    return () => {
      alive = false;
      cancelAnimationFrame(raf);
      window.removeEventListener("resize", onResize);
    };
  }, []);

  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-x-0 top-0 z-0 h-screen overflow-hidden"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_color-mix(in_oklab,_var(--foreground)_4%,_transparent)_0%,_transparent_72%)]" />
      <canvas ref={canvasRef} className="absolute inset-0 h-full w-full" />
      <div className="absolute inset-x-0 bottom-0 h-24 bg-gradient-to-t from-background to-transparent" />
    </div>
  );
}
