/**
 * Workspace Templates for GCC In-House Pilots
 *
 * These templates define pre-configured policy profiles that can be applied
 * during workspace setup. Each template configures:
 * - Allowed workflows
 * - Allowed jurisdictions
 * - Allowed input/output languages
 * - Feature flags
 * - Default language and jurisdiction profile
 *
 * JURISDICTION PARITY:
 * UAE and KSA are first-class jurisdictions with equal template support.
 * Each jurisdiction has templates tailored to local legal practice patterns.
 */

export type JurisdictionRegion = 'UAE' | 'KSA';
export type PrimaryJurisdiction = 'UAE' | 'KSA' | 'DIFC' | 'ADGM';
export type DataResidencyPolicy = 'UAE' | 'KSA' | 'GCC';

export interface WorkspaceTemplate {
  /** Unique identifier for the template */
  id: string;
  /** Display name shown in dropdown */
  name: string;
  /** Description of the template use case */
  description: string;
  /** Region this template is designed for (UAE or KSA) */
  region: JurisdictionRegion;
  /** Recommended primary jurisdiction for this template */
  recommendedJurisdiction: PrimaryJurisdiction;
  /** Recommended data residency policy for this template */
  recommendedDataResidency: DataResidencyPolicy;
  /** Policy profile configuration */
  policyConfig: {
    allowed_workflows: string[];
    allowed_jurisdictions: string[];
    allowed_input_languages: string[];
    allowed_output_languages: string[];
    feature_flags: Record<string, boolean>;
  };
  /** Workspace defaults */
  workspaceDefaults: {
    default_language: 'en' | 'ar' | 'mixed';
    jurisdiction_profile:
      | 'UAE_DEFAULT'
      | 'DIFC_DEFAULT'
      | 'ADGM_DEFAULT'
      | 'KSA_DEFAULT';
  };
}

// =============================================================================
// UAE Templates
// =============================================================================

/**
 * UAE In-House (General Counsel) Template
 *
 * Full access to all workflows for general counsel teams.
 * Supports both English and Arabic in mixed mode.
 */
export const UAE_IN_HOUSE_GENERAL_COUNSEL: WorkspaceTemplate = {
  id: 'uae_in_house_gc',
  name: 'UAE In-House (General Counsel)',
  description:
    'Full access to legal research and contract review for in-house legal teams',
  region: 'UAE',
  recommendedJurisdiction: 'UAE',
  recommendedDataResidency: 'UAE',
  policyConfig: {
    allowed_workflows: ['LEGAL_RESEARCH_V1', 'CONTRACT_REVIEW_V1'],
    allowed_jurisdictions: ['UAE', 'DIFC', 'ADGM', 'KSA'],
    allowed_input_languages: ['en', 'ar', 'mixed'],
    allowed_output_languages: ['en', 'ar'],
    feature_flags: {
      law_firm_mode: false,
    },
  },
  workspaceDefaults: {
    default_language: 'mixed',
    jurisdiction_profile: 'UAE_DEFAULT',
  },
};

/**
 * UAE Procurement (Contract-heavy) Template
 *
 * Focused on contract review for procurement teams.
 * English as default language for clarity in contracts.
 */
export const UAE_PROCUREMENT_CONTRACT: WorkspaceTemplate = {
  id: 'uae_procurement_contract',
  name: 'UAE Procurement (Contract-heavy)',
  description: 'Contract review focused template for procurement teams',
  region: 'UAE',
  recommendedJurisdiction: 'UAE',
  recommendedDataResidency: 'UAE',
  policyConfig: {
    allowed_workflows: ['CONTRACT_REVIEW_V1'],
    allowed_jurisdictions: ['UAE', 'DIFC', 'ADGM', 'KSA'],
    allowed_input_languages: ['en', 'ar', 'mixed'],
    allowed_output_languages: ['en', 'ar'],
    feature_flags: {
      law_firm_mode: false,
    },
  },
  workspaceDefaults: {
    default_language: 'en',
    jurisdiction_profile: 'UAE_DEFAULT',
  },
};

/**
 * UAE Compliance Template
 *
 * Legal research focused for compliance teams.
 * English as default for regulatory analysis.
 */
export const UAE_COMPLIANCE: WorkspaceTemplate = {
  id: 'uae_compliance',
  name: 'UAE Compliance',
  description: 'Legal research focused template for compliance teams',
  region: 'UAE',
  recommendedJurisdiction: 'UAE',
  recommendedDataResidency: 'UAE',
  policyConfig: {
    allowed_workflows: ['LEGAL_RESEARCH_V1'],
    allowed_jurisdictions: ['UAE', 'DIFC', 'ADGM', 'KSA'],
    allowed_input_languages: ['en', 'ar', 'mixed'],
    allowed_output_languages: ['en', 'ar'],
    feature_flags: {
      law_firm_mode: false,
    },
  },
  workspaceDefaults: {
    default_language: 'en',
    jurisdiction_profile: 'UAE_DEFAULT',
  },
};

// =============================================================================
// KSA Templates (First-Class Jurisdiction Parity)
// =============================================================================

/**
 * KSA In-House (General Counsel) Template
 *
 * Full access to all workflows for Saudi in-house legal teams.
 * Arabic-first by default, reflecting local practice.
 */
export const KSA_IN_HOUSE_GENERAL_COUNSEL: WorkspaceTemplate = {
  id: 'ksa_in_house_gc',
  name: 'KSA In-House (General Counsel)',
  description:
    'Full access to legal research and contract review for Saudi in-house legal teams',
  region: 'KSA',
  recommendedJurisdiction: 'KSA',
  recommendedDataResidency: 'KSA',
  policyConfig: {
    allowed_workflows: ['LEGAL_RESEARCH_V1', 'CONTRACT_REVIEW_V1'],
    allowed_jurisdictions: ['KSA'],
    allowed_input_languages: ['ar', 'en', 'mixed'],
    allowed_output_languages: ['ar', 'en'],
    feature_flags: {
      law_firm_mode: false,
    },
  },
  workspaceDefaults: {
    default_language: 'ar',
    jurisdiction_profile: 'KSA_DEFAULT',
  },
};

/**
 * KSA Procurement (Contract-heavy) Template
 *
 * Focused on contract review for Saudi procurement teams.
 * Arabic-first by default for government and local contracts.
 */
export const KSA_PROCUREMENT_CONTRACT: WorkspaceTemplate = {
  id: 'ksa_procurement_contract',
  name: 'KSA Procurement (Contract-heavy)',
  description: 'Contract review focused template for Saudi procurement teams',
  region: 'KSA',
  recommendedJurisdiction: 'KSA',
  recommendedDataResidency: 'KSA',
  policyConfig: {
    allowed_workflows: ['CONTRACT_REVIEW_V1'],
    allowed_jurisdictions: ['KSA'],
    allowed_input_languages: ['ar', 'en', 'mixed'],
    allowed_output_languages: ['ar', 'en'],
    feature_flags: {
      law_firm_mode: false,
    },
  },
  workspaceDefaults: {
    default_language: 'ar',
    jurisdiction_profile: 'KSA_DEFAULT',
  },
};

/**
 * All available workspace templates
 *
 * Templates are grouped by region (UAE, KSA) with equal first-class status.
 * No region is treated as "default" - the first selection determines all defaults.
 */
export const WORKSPACE_TEMPLATES: WorkspaceTemplate[] = [
  // UAE Templates
  UAE_IN_HOUSE_GENERAL_COUNSEL,
  UAE_PROCUREMENT_CONTRACT,
  UAE_COMPLIANCE,
  // KSA Templates (First-Class Parity)
  KSA_IN_HOUSE_GENERAL_COUNSEL,
  KSA_PROCUREMENT_CONTRACT,
];

/**
 * Get templates filtered by region
 */
export function getTemplatesByRegion(
  region: JurisdictionRegion
): WorkspaceTemplate[] {
  return WORKSPACE_TEMPLATES.filter(t => t.region === region);
}

/**
 * Get all available regions
 */
export function getAvailableRegions(): JurisdictionRegion[] {
  return ['UAE', 'KSA'];
}

/**
 * Get a template by its ID
 */
export function getTemplateById(id: string): WorkspaceTemplate | undefined {
  return WORKSPACE_TEMPLATES.find(t => t.id === id);
}

/**
 * Get the template name for display
 */
export function getTemplateName(id: string): string {
  const template = getTemplateById(id);
  return template?.name ?? 'Unknown Template';
}

/**
 * LocalStorage key for storing the selected template
 */
export const TEMPLATE_STORAGE_KEY = 'aiden_workspace_template';

/**
 * Store the selected template ID in localStorage
 */
export function setStoredTemplateId(templateId: string): void {
  if (typeof window !== 'undefined') {
    localStorage.setItem(TEMPLATE_STORAGE_KEY, templateId);
  }
}

/**
 * Get the stored template ID from localStorage
 */
export function getStoredTemplateId(): string | null {
  if (typeof window !== 'undefined') {
    return localStorage.getItem(TEMPLATE_STORAGE_KEY);
  }
  return null;
}
