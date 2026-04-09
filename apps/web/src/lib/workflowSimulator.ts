'use client';

export interface WorkflowSimulationTick {
  progress: number;
  phase: 'starting' | 'processing' | 'finalizing';
}

export interface WorkflowSimulationResult {
  durationMs: number;
}

function easeOutCubic(value: number): number {
  return 1 - Math.pow(1 - value, 3);
}

function computeProgress(elapsedMs: number, durationMs: number): number {
  const phase1 = Math.min(1500, durationMs * 0.25);
  const phase3 = Math.min(500, durationMs * 0.12);
  const phase2 = Math.max(500, durationMs - phase1 - phase3);

  if (elapsedMs <= phase1) {
    return 40 * easeOutCubic(elapsedMs / phase1);
  }

  if (elapsedMs <= phase1 + phase2) {
    const progress = (elapsedMs - phase1) / phase2;
    return 40 + 40 * (1 - Math.pow(1 - progress, 1.6));
  }

  const progress = Math.min(1, (elapsedMs - phase1 - phase2) / phase3);
  return 80 + 20 * easeOutCubic(progress);
}

function getPhase(progress: number): WorkflowSimulationTick['phase'] {
  if (progress < 40) return 'starting';
  if (progress < 80) return 'processing';
  return 'finalizing';
}

export async function runWorkflowSimulation(options: {
  onTick: (tick: WorkflowSimulationTick) => void;
  minDurationMs?: number;
  maxDurationMs?: number;
}): Promise<WorkflowSimulationResult> {
  const durationMs =
    (options.minDurationMs ?? 4000) +
    Math.floor(
      Math.random() *
        ((options.maxDurationMs ?? 9000) - (options.minDurationMs ?? 4000))
    );

  const startedAt = performance.now();

  return new Promise(resolve => {
    const step = () => {
      const elapsed = performance.now() - startedAt;
      const progress = Math.min(100, computeProgress(elapsed, durationMs));

      options.onTick({
        progress,
        phase: getPhase(progress),
      });

      if (elapsed >= durationMs) {
        options.onTick({ progress: 100, phase: 'finalizing' });
        resolve({ durationMs });
        return;
      }

      window.setTimeout(step, 120);
    };

    step();
  });
}
