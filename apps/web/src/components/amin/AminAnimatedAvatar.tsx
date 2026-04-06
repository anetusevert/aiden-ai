'use client';

import { useEffect, useRef, memo } from 'react';
import type { AminAvatarState } from './AminAvatar';

interface AminAnimatedAvatarProps {
  size: number;
  state: AminAvatarState;
}

/* ─── Facial-feature coordinates (fraction of visible ring area) ──── */
const L_EYE = { x: 0.36, y: 0.39 };
const R_EYE = { x: 0.64, y: 0.39 };
const EYES = [L_EYE, R_EYE];

const PUPIL_TRACK = 0.025;
const REFLECT_R = 0.012;
const EYELID = { rx: 0.055, ry: 0.04 };
const MOUTH = { x: 0.5, y: 0.61 };
const MOUTH_W = 0.065;
const MOUTH_H_REST = 0.004;
const SKIN = '#c8956c';

const BLINK_MS: Record<string, [number, number]> = {
  idle: [3000, 6000],
  thinking: [6000, 9000],
  speaking: [2000, 4000],
  listening: [3500, 6000],
  sleeping: [Infinity, Infinity],
  success: [1500, 3000],
};

const LERP = 0.06;
const BLINK_DUR = 220;

export const AminAnimatedAvatar = memo(function AminAnimatedAvatar({
  size,
  state,
}: AminAnimatedAvatarProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const rafRef = useRef(0);
  const mouseRef = useRef({ x: 0, y: 0 });
  const centerRef = useRef({ x: 0, y: 0 });
  const headRef = useRef({ tx: 0, ty: 0, r: 0 });
  const blinkRef = useRef({ on: false, t0: 0, next: 0 });
  const stateRef = useRef(state);
  stateRef.current = state;

  useEffect(() => {
    const onMove = (e: MouseEvent) => {
      mouseRef.current = { x: e.clientX, y: e.clientY };
    };
    mouseRef.current = {
      x: window.innerWidth / 2,
      y: window.innerHeight / 2,
    };
    blinkRef.current.next = Date.now() + 2000 + Math.random() * 3000;
    window.addEventListener('mousemove', onMove, { passive: true });
    return () => window.removeEventListener('mousemove', onMove);
  }, []);

  useEffect(() => {
    const update = () => {
      const el = canvasRef.current;
      if (!el) return;
      const r = el.getBoundingClientRect();
      centerRef.current = { x: r.left + r.width / 2, y: r.top + r.height / 2 };
    };
    update();
    window.addEventListener('scroll', update, { passive: true });
    window.addEventListener('resize', update, { passive: true });
    const iv = setInterval(update, 2000);
    return () => {
      window.removeEventListener('scroll', update);
      window.removeEventListener('resize', update);
      clearInterval(iv);
    };
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    const dpr = window.devicePixelRatio || 1;
    canvas.width = size * dpr;
    canvas.height = size * dpr;
    ctx.scale(dpr, dpr);

    let running = true;
    const bk = blinkRef.current;
    const hd = headRef.current;

    const frame = () => {
      if (!running) return;
      ctx.clearRect(0, 0, size, size);

      const now = Date.now();
      const s = stateRef.current;
      const { x: mx, y: my } = mouseRef.current;
      const { x: cx, y: cy } = centerRef.current;

      const ndx = Math.max(
        -1,
        Math.min(1, (mx - cx) / (window.innerWidth * 0.4))
      );
      const ndy = Math.max(
        -1,
        Math.min(1, (my - cy) / (window.innerHeight * 0.4))
      );

      /* ──── Head tilt ──────────────────────────────────── */
      const img = imgRef.current;
      if (img) {
        let ttx: number, tty: number, tr: number;
        if (s === 'sleeping') {
          ttx = 0;
          tty = 1;
          tr = 5;
        } else if (s === 'thinking') {
          const t = now / 3000;
          ttx = Math.sin(t) * 1.5;
          tty = -0.5;
          tr = Math.sin(t * 0.7) * 2;
        } else if (s === 'success') {
          const bounce =
            Math.sin(now / 150) * Math.max(0, 1 - (now % 2000) / 600) * 4;
          ttx = 0;
          tty = bounce;
          tr = 0;
        } else {
          const breathe = Math.sin(now / 2500) * 0.4;
          ttx = ndx * 2;
          tty = ndy * 1.2 + breathe;
          tr = -ndx * 1.5;
        }
        hd.tx += (ttx - hd.tx) * LERP;
        hd.ty += (tty - hd.ty) * LERP;
        hd.r += (tr - hd.r) * LERP;
        img.style.transform = `translate(${hd.tx.toFixed(2)}px, ${hd.ty.toFixed(2)}px) rotate(${hd.r.toFixed(2)}deg)`;
      }

      /* ──── Blink ──────────────────────────────────────── */
      if (!bk.on && now >= bk.next && s !== 'sleeping') {
        bk.on = true;
        bk.t0 = now;
      }
      let lid = s === 'sleeping' ? 1 : 0;
      if (bk.on) {
        const el = now - bk.t0;
        if (el >= BLINK_DUR) {
          bk.on = false;
          const [lo, hi] = BLINK_MS[s] ?? [3000, 6000];
          bk.next = now + lo + Math.random() * (hi - lo);
        } else {
          const half = BLINK_DUR / 2;
          lid = el < half ? el / half : 1 - (el - half) / half;
        }
      }

      /* ──── Draw eyelids ───────────────────────────────── */
      if (lid > 0.05) {
        for (const eye of EYES) {
          ctx.beginPath();
          ctx.ellipse(
            eye.x * size,
            eye.y * size,
            EYELID.rx * size,
            EYELID.ry * size * lid,
            0,
            0,
            Math.PI * 2
          );
          ctx.fillStyle = SKIN;
          ctx.fill();
        }
      }

      /* ──── Draw eye reflections ───────────────────────── */
      if (lid < 0.7 && s !== 'sleeping') {
        const track = PUPIL_TRACK * size;
        for (const eye of EYES) {
          let ox: number, oy: number;
          if (s === 'thinking') {
            const t = now / 2000;
            ox = Math.sin(t) * track * 0.6;
            oy = -track * 0.4;
          } else if (s === 'listening') {
            ox = ndx * track * 0.2;
            oy = ndy * track * 0.15;
          } else {
            ox = ndx * track;
            oy = ndy * track;
          }
          const px = eye.x * size + ox;
          const py = eye.y * size + oy;
          const r = Math.max(REFLECT_R * size, 0.8);

          ctx.beginPath();
          ctx.arc(px, py, r, 0, Math.PI * 2);
          ctx.fillStyle = 'rgba(255,255,255,0.88)';
          ctx.fill();

          ctx.beginPath();
          ctx.arc(
            px + r * 0.45,
            py - r * 0.45,
            Math.max(r * 0.35, 0.4),
            0,
            Math.PI * 2
          );
          ctx.fillStyle = 'rgba(255,255,255,0.55)';
          ctx.fill();
        }
      }

      /* ──── Draw mouth (speaking) ──────────────────────── */
      if (s === 'speaking') {
        const mouthX = MOUTH.x * size;
        const mouthY = MOUTH.y * size;
        const w = MOUTH_W * size;
        const openness = (Math.sin(now / 100) + 1) / 2;
        const h = (MOUTH_H_REST + openness * 0.022) * size;
        ctx.beginPath();
        ctx.ellipse(mouthX, mouthY, w / 2, Math.max(h, 0.8), 0, 0, Math.PI * 2);
        ctx.fillStyle = 'rgba(55,18,18,0.40)';
        ctx.fill();
      }

      rafRef.current = requestAnimationFrame(frame);
    };

    rafRef.current = requestAnimationFrame(frame);
    return () => {
      running = false;
      cancelAnimationFrame(rafRef.current);
    };
  }, [size]);

  return (
    <>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        ref={imgRef}
        src="/brand/amin-avatar.png"
        className="amin-avatar-img"
        alt="Amin"
        draggable={false}
      />
      <canvas
        ref={canvasRef}
        className="amin-animated-canvas"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          width: '100%',
          height: '100%',
          pointerEvents: 'none',
          zIndex: 3,
          borderRadius: '50%',
        }}
      />
    </>
  );
});
