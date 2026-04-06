export const SOURCE_COLORS: Record<string, string> = {
  legislation: '#638cff',
  jurisprudence: '#a78bfa',
  news: '#f87171',
  professional: '#34d399',
  business_law: '#f59e0b',
  consultation: '#d4a017',
  analysis: '#38bdf8',
  tax_law: '#fb923c',
  financial_regulation: '#94a3b8',
};

export const SOURCE_NAME_COLORS: Record<string, string> = {
  'Umm Al-Qura': '#638cff',
  'Bureau of Experts': '#638cff',
  'Scientific Judicial Portal': '#a78bfa',
  'Saudi Press Agency': '#f87171',
  'Saudi Bar Association': '#34d399',
  'Ministry of Investment': '#f59e0b',
  'Istitlaa Public Consultations': '#d4a017',
  'JD Supra - Saudi Arabia': '#38bdf8',
  'JD Supra - Middle East': '#38bdf8',
  'Mondaq - Saudi Arabia': '#38bdf8',
  'Mondaq - UAE': '#38bdf8',
  'Al Tamimi & Company': '#38bdf8',
  'Lexology - Middle East': '#38bdf8',
  'ZATCA (Zakat, Tax & Customs)': '#fb923c',
  'SAMA (Saudi Central Bank)': '#94a3b8',
  'Zawya - Law & Governance': '#38bdf8',
};

export const CATEGORY_ICONS: Record<string, string> = {
  legislation: '📜',
  jurisprudence: '⚖️',
  consultation: '🏛️',
  business_law: '💼',
  professional: '👔',
  analysis: '📊',
  news: '📰',
  tax_law: '🧾',
  financial_regulation: '🏦',
};

export const CATEGORY_LABELS: Record<string, string> = {
  legislation: 'Legislation',
  jurisprudence: 'Jurisprudence',
  consultation: 'Consultations',
  business_law: 'Business Law',
  professional: 'Professional',
  analysis: 'Analysis',
  news: 'News',
  tax_law: 'Tax Law',
  financial_regulation: 'Financial Regulation',
};

export const JURISDICTIONS = ['KSA', 'UAE', 'GCC', 'Qatar'] as const;

export const CATEGORIES = [
  { key: '', label: 'All', icon: '' },
  { key: 'legislation', label: 'Legislation', icon: '📜' },
  { key: 'jurisprudence', label: 'Jurisprudence', icon: '⚖️' },
  { key: 'consultation', label: 'Consultations', icon: '🏛️' },
  { key: 'business_law', label: 'Business Law', icon: '💼' },
  { key: 'professional', label: 'Professional', icon: '👔' },
  { key: 'analysis', label: 'Analysis', icon: '📊' },
  { key: 'news', label: 'News', icon: '📰' },
  { key: 'tax_law', label: 'Tax Law', icon: '🧾' },
  { key: 'financial_regulation', label: 'Financial Reg.', icon: '🏦' },
] as const;
