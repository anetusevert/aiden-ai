/**
 * Client-side workflow usage tracking.
 *
 * Stores lightweight usage events in localStorage so the sidebar can
 * compute frequency and recency scores without a backend dependency.
 * Events older than 90 days are pruned automatically.
 */

const STORAGE_KEY = 'heyamin-workflow-usage';
const MAX_AGE_MS = 90 * 24 * 60 * 60 * 1000; // 90 days
const MAX_EVENTS = 500;

interface UsageEvent {
  workflow_id: string;
  ts: number; // epoch ms
}

function readEvents(): UsageEvent[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as UsageEvent[];
  } catch {
    return [];
  }
}

function writeEvents(events: UsageEvent[]): void {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(events));
  } catch {
    // quota exceeded — prune more aggressively
    const trimmed = events.slice(-Math.floor(MAX_EVENTS / 2));
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(trimmed));
    } catch {
      // give up
    }
  }
}

function prune(events: UsageEvent[]): UsageEvent[] {
  const cutoff = Date.now() - MAX_AGE_MS;
  const valid = events.filter(e => e.ts > cutoff);
  return valid.length > MAX_EVENTS ? valid.slice(-MAX_EVENTS) : valid;
}

/** Record that the user accessed a workflow. */
export function trackWorkflowUsage(workflowId: string): void {
  const events = prune(readEvents());
  events.push({ workflow_id: workflowId, ts: Date.now() });
  writeEvents(events);
}

/** Get the timestamp of the most recent access for each workflow. */
export function getRecentWorkflows(): Record<string, number> {
  const events = readEvents();
  const recent: Record<string, number> = {};
  for (const e of events) {
    if (!recent[e.workflow_id] || e.ts > recent[e.workflow_id]) {
      recent[e.workflow_id] = e.ts;
    }
  }
  return recent;
}

/** Get access count for each workflow within the last N days. */
export function getWorkflowFrequency(
  days: number = 30
): Record<string, number> {
  const cutoff = Date.now() - days * 24 * 60 * 60 * 1000;
  const events = readEvents().filter(e => e.ts > cutoff);
  const freq: Record<string, number> = {};
  for (const e of events) {
    freq[e.workflow_id] = (freq[e.workflow_id] || 0) + 1;
  }
  return freq;
}

/** Get the top N workflows by combined frequency + recency score. */
export function getTopWorkflows(
  n: number = 7
): { workflow_id: string; score: number }[] {
  const freq = getWorkflowFrequency(30);
  const recent = getRecentWorkflows();
  const now = Date.now();

  const allIds = Array.from(
    new Set([...Object.keys(freq), ...Object.keys(recent)])
  );
  const scored: { workflow_id: string; score: number }[] = [];

  for (const id of allIds) {
    const f = freq[id] || 0;
    const r = recent[id] || 0;

    const maxFreq = Math.max(1, ...Object.values(freq));
    const freqNorm = f / maxFreq;

    const ageMs = now - r;
    const recencyNorm = Math.max(0, 1 - ageMs / (30 * 24 * 60 * 60 * 1000));

    const score = freqNorm * 0.6 + recencyNorm * 0.4;
    scored.push({ workflow_id: id, score });
  }

  scored.sort((a, b) => b.score - a.score);
  return scored.slice(0, n);
}
