export const SOURCE_COLORS: Record<string, string> = {
  legislation: 'rgba(255,255,255,0.9)',
  jurisprudence: 'rgba(255,255,255,0.82)',
  news: 'rgba(255,255,255,0.72)',
  professional: 'rgba(255,255,255,0.88)',
  business_law: 'rgba(255,255,255,0.78)',
  consultation: 'rgba(255,255,255,0.85)',
  analysis: 'rgba(255,255,255,0.8)',
  tax_law: 'rgba(255,255,255,0.75)',
  financial_regulation: 'rgba(255,255,255,0.68)',
};

export const SOURCE_NAME_COLORS: Record<string, string> = {
  'Umm Al-Qura': 'rgba(255,255,255,0.9)',
  'Bureau of Experts': 'rgba(255,255,255,0.88)',
  'Scientific Judicial Portal': 'rgba(255,255,255,0.82)',
  'Saudi Press Agency': 'rgba(255,255,255,0.72)',
  'Saudi Bar Association': 'rgba(255,255,255,0.88)',
  'Ministry of Investment': 'rgba(255,255,255,0.78)',
  'Istitlaa Public Consultations': 'rgba(255,255,255,0.85)',
  'JD Supra - Saudi Arabia': 'rgba(255,255,255,0.8)',
  'JD Supra - Middle East': 'rgba(255,255,255,0.8)',
  'Mondaq - Saudi Arabia': 'rgba(255,255,255,0.8)',
  'Mondaq - UAE': 'rgba(255,255,255,0.8)',
  'Al Tamimi & Company': 'rgba(255,255,255,0.8)',
  'Lexology - Middle East': 'rgba(255,255,255,0.8)',
  'ZATCA (Zakat, Tax & Customs)': 'rgba(255,255,255,0.75)',
  'SAMA (Saudi Central Bank)': 'rgba(255,255,255,0.68)',
  'Zawya - Law & Governance': 'rgba(255,255,255,0.8)',
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
