/**
 * Human-readable cron descriptions for common 5-field patterns used in the app.
 * Returns the raw string when no known pattern matches.
 */

const WEEKDAYS = [
  'Sunday',
  'Monday',
  'Tuesday',
  'Wednesday',
  'Thursday',
  'Friday',
  'Saturday',
] as const;

function pad2(n: number): string {
  return n < 10 ? `0${n}` : String(n);
}

function ordinalDay(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return `${n}st`;
  if (mod10 === 2 && mod100 !== 12) return `${n}nd`;
  if (mod10 === 3 && mod100 !== 13) return `${n}rd`;
  return `${n}th`;
}

/** Parse a single cron field as fixed integer or * */
function fixedInt(part: string): number | null {
  if (part === '*' || part === '?' || part === '') return null;
  const n = parseInt(part, 10);
  return Number.isFinite(n) ? n : null;
}

/**
 * Converts a 5-field cron expression to a human-readable string.
 */
export function describeCron(cron: string): string {
  const trimmed = cron.trim();
  if (!trimmed) return trimmed;

  const parts = trimmed.split(/\s+/);
  if (parts.length !== 5) return trimmed;

  const [min, hour, dom, month, dow] = parts;

  // Every N hours: "0 */N * * *"
  const hourStepMatch = hour.match(/^\*\/(\d+)$/);
  if (
    hourStepMatch &&
    min === '0' &&
    dom === '*' &&
    month === '*' &&
    dow === '*'
  ) {
    const step = parseInt(hourStepMatch[1], 10);
    if (step === 1) return 'Every hour';
    return `Every ${step} hours`;
  }

  // Every N minutes: "*/N * * * *"
  const minStepMatch = min.match(/^\*\/(\d+)$/);
  if (
    minStepMatch &&
    hour === '*' &&
    dom === '*' &&
    month === '*' &&
    dow === '*'
  ) {
    const step = parseInt(minStepMatch[1], 10);
    if (step === 1) return 'Every minute';
    return `Every ${step} minutes`;
  }

  // Daily at HH:MM
  const h = fixedInt(hour);
  const m = fixedInt(min);
  if (
    h !== null &&
    m !== null &&
    dom === '*' &&
    month === '*' &&
    (dow === '*' || dow === '?')
  ) {
    return `Every day at ${pad2(h)}:${pad2(m)}`;
  }

  // Weekly on day D at HH:MM — dow single digit 0-6
  if (
    h !== null &&
    m !== null &&
    dom === '*' &&
    month === '*' &&
    /^\d$/.test(dow)
  ) {
    const d = parseInt(dow, 10);
    if (d >= 0 && d <= 6) {
      return `Every ${WEEKDAYS[d]} at ${pad2(h)}:${pad2(m)}`;
    }
  }

  // Monthly on day-of-month at HH:MM
  const d = fixedInt(dom);
  if (
    h !== null &&
    m !== null &&
    d !== null &&
    d >= 1 &&
    d <= 31 &&
    month === '*' &&
    (dow === '*' || dow === '?')
  ) {
    return `Every ${ordinalDay(d)} of the month at ${pad2(h)}:${pad2(m)}`;
  }

  return trimmed;
}

/**
 * Formats a duration in seconds as a compact string (e.g. "45s", "2m 14s", "1h 3m").
 */
export function formatDuration(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return '—';
  if (seconds < 60) return `${Math.floor(seconds)}s`;

  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);

  if (mins < 60) {
    if (secs === 0) return `${mins}m`;
    return `${mins}m ${secs}s`;
  }

  const hrs = Math.floor(mins / 60);
  const remM = mins % 60;
  if (remM === 0) return `${hrs}h`;
  return `${hrs}h ${remM}m`;
}
