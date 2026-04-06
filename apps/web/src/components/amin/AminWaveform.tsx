'use client';

import { useEffect, useRef, useCallback } from 'react';
import { getAminAnalyser } from '@/lib/aminAudio';

interface AminWaveformProps {
  size: number;
}

const BAR_COUNT = 16;
const MIN_HEIGHT = 2;
const MAX_HEIGHT = 20;
const BAR_WIDTH = 2;

export function AminWaveform({ size }: AminWaveformProps) {
  const barsRef = useRef<(SVGRectElement | null)[]>([]);
  const rafRef = useRef<number>(0);
  const arcRadius = size * 0.65;
  const svgSize = arcRadius * 2 + MAX_HEIGHT * 2 + 4;

  const getBarTransform = useCallback(
    (index: number) => {
      const angle = Math.PI + (Math.PI * index) / (BAR_COUNT - 1);
      const cx = svgSize / 2;
      const cy = svgSize / 2 - size * 0.1;
      const x = cx + arcRadius * Math.cos(angle);
      const y = cy + arcRadius * Math.sin(angle);
      const rotation = (angle * 180) / Math.PI + 90;
      return { x, y, rotation };
    },
    [arcRadius, svgSize, size]
  );

  useEffect(() => {
    let running = true;

    const animate = () => {
      if (!running) return;

      const analyser = getAminAnalyser();
      const bars = barsRef.current;

      if (analyser) {
        const data = new Uint8Array(analyser.frequencyBinCount);
        analyser.getByteFrequencyData(data);
        const step = Math.max(1, Math.floor(data.length / BAR_COUNT));

        for (let i = 0; i < BAR_COUNT; i++) {
          const bar = bars[i];
          if (!bar) continue;
          const amp = data[i * step] ?? 0;
          const h = MIN_HEIGHT + (amp / 255) * (MAX_HEIGHT - MIN_HEIGHT);
          bar.setAttribute('height', String(h));
          bar.setAttribute('opacity', String(0.5 + (amp / 255) * 0.5));
        }
      } else {
        const now = Date.now();
        for (let i = 0; i < BAR_COUNT; i++) {
          const bar = bars[i];
          if (!bar) continue;
          const h = Math.abs(Math.sin(now / 200 + i * 0.4)) * 16 + MIN_HEIGHT;
          bar.setAttribute('height', String(h));
          bar.setAttribute('opacity', String(0.5 + (h / MAX_HEIGHT) * 0.5));
        }
      }

      rafRef.current = requestAnimationFrame(animate);
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => {
      running = false;
      cancelAnimationFrame(rafRef.current);
    };
  }, []);

  return (
    <svg
      className="amin-waveform-svg"
      width={svgSize}
      height={svgSize / 2 + MAX_HEIGHT}
      viewBox={`0 ${svgSize / 2 - MAX_HEIGHT} ${svgSize} ${svgSize / 2 + MAX_HEIGHT}`}
      style={{ bottom: -(svgSize / 4) }}
    >
      {Array.from({ length: BAR_COUNT }).map((_, i) => {
        const { x, y, rotation } = getBarTransform(i);
        return (
          <rect
            key={i}
            ref={el => {
              barsRef.current[i] = el;
            }}
            x={x - BAR_WIDTH / 2}
            y={y}
            width={BAR_WIDTH}
            height={MIN_HEIGHT}
            rx={BAR_WIDTH / 2}
            fill="#d4a017"
            opacity={0.5}
            transform={`rotate(${rotation} ${x} ${y})`}
          />
        );
      })}
    </svg>
  );
}
