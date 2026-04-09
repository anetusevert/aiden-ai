export const PRESET_CRONS = ['0 2 * * 0', '0 2 * * 1', '0 2 1 * *'] as const;

export const CUSTOM_SENTINEL = '__custom__';

export const CONNECTOR_OPTIONS = [
  { value: 'ksa_boe', label: 'KSA Bureau of Experts' },
  { value: 'ksa_moj', label: 'KSA Ministry of Justice' },
  { value: 'ksa_uaq', label: 'KSA Umm Al-Qura Gazette' },
  { value: 'uae_moj', label: 'UAE Ministry of Justice' },
  { value: 'qatar_almeezan', label: 'Qatar Al Meezan' },
] as const;

export const CONNECTOR_DEFAULTS: Record<
  string,
  { display_name: string; jurisdiction: string; source_url: string }
> = {
  ksa_boe: {
    display_name: 'KSA Bureau of Experts',
    jurisdiction: 'KSA',
    source_url: 'https://laws.boe.gov.sa',
  },
  ksa_moj: {
    display_name: 'KSA Ministry of Justice',
    jurisdiction: 'KSA',
    source_url: 'https://www.moj.gov.sa',
  },
  ksa_uaq: {
    display_name: 'KSA Umm Al-Qura Gazette',
    jurisdiction: 'KSA',
    source_url: 'https://www.ummulqura.org.sa',
  },
  uae_moj: {
    display_name: 'UAE Ministry of Justice',
    jurisdiction: 'UAE',
    source_url: 'https://www.moj.gov.ae',
  },
  qatar_almeezan: {
    display_name: 'Qatar Al Meezan',
    jurisdiction: 'QATAR',
    source_url: 'https://www.almeezan.qa',
  },
};

export const SCHEDULE_SELECT_OPTIONS = [
  { value: '', label: 'Manual only' },
  { value: '0 2 * * 0', label: 'Weekly (Sunday 2am)' },
  { value: '0 2 * * 1', label: 'Weekly (Monday 2am)' },
  { value: '0 2 1 * *', label: 'Monthly (1st of month)' },
  { value: CUSTOM_SENTINEL, label: 'Custom cron expression...' },
];

export function schedulePayloadFromForm(
  scheduleValue: string,
  customCron: string
): string | null {
  if (scheduleValue === '') return null;
  if (scheduleValue === CUSTOM_SENTINEL) {
    const trimmed = customCron.trim();
    return trimmed.length ? trimmed : null;
  }
  return scheduleValue;
}

export function initialScheduleSelect(cron: string | null): {
  value: string;
  custom: string;
} {
  if (!cron) return { value: '', custom: '' };
  if ((PRESET_CRONS as readonly string[]).includes(cron)) {
    return { value: cron, custom: '' };
  }
  return { value: CUSTOM_SENTINEL, custom: cron };
}
