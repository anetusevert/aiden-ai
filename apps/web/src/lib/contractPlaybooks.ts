/**
 * Contract Review Playbooks v1
 *
 * Playbooks prefill contract review settings and optionally provide prompt hints
 * for productized contract review experiences. They don't change backend behavior
 * in v1 - prompt_hint is UI-only for now.
 */

import { ContractReviewMode, ContractFocusArea } from './apiClient';

export type PlaybookRegion = 'UAE' | 'KSA';

export interface ContractPlaybook {
  /** Unique identifier for the playbook */
  id: string;
  /** Display name */
  name: string;
  /** Region (UAE or KSA) for grouping */
  region: PlaybookRegion;
  /** Default review mode */
  default_review_mode: ContractReviewMode;
  /** Default focus areas */
  default_focus_areas: ContractFocusArea[];
  /** Recommended output language */
  recommended_output_language: 'en' | 'ar';
  /**
   * Optional prompt hint displayed to user (read-only).
   * NOT sent to API in v1 - future enhancement.
   */
  prompt_hint?: string;
}

// ---------------------------------------------------------------------------
// UAE Playbooks
// ---------------------------------------------------------------------------

export const UAE_PROCUREMENT_MSA: ContractPlaybook = {
  id: 'uae_procurement_msa',
  name: 'UAE Procurement MSA',
  region: 'UAE',
  default_review_mode: 'standard',
  default_focus_areas: ['liability', 'termination', 'payment', 'governing_law'],
  recommended_output_language: 'en',
  prompt_hint:
    'Prioritize UAE governing law clauses, DIFC/ADGM considerations, and standard procurement terms.',
};

export const UAE_NDA: ContractPlaybook = {
  id: 'uae_nda',
  name: 'UAE NDA',
  region: 'UAE',
  default_review_mode: 'quick',
  default_focus_areas: ['confidentiality', 'termination', 'governing_law'],
  recommended_output_language: 'en',
  prompt_hint:
    'Focus on confidentiality scope, permitted disclosures, term/survival periods, and UAE law compliance.',
};

// ---------------------------------------------------------------------------
// KSA Playbooks (Arabic-first)
// ---------------------------------------------------------------------------

export const KSA_PROCUREMENT_MSA: ContractPlaybook = {
  id: 'ksa_procurement_msa',
  name: 'KSA Procurement MSA',
  region: 'KSA',
  default_review_mode: 'standard',
  default_focus_areas: ['liability', 'termination', 'payment', 'governing_law'],
  recommended_output_language: 'ar',
  prompt_hint:
    'Prioritize Saudi law compliance, Sharia considerations, and government procurement regulations.',
};

export const KSA_NDA: ContractPlaybook = {
  id: 'ksa_nda',
  name: 'KSA NDA',
  region: 'KSA',
  default_review_mode: 'quick',
  default_focus_areas: ['confidentiality', 'termination', 'governing_law'],
  recommended_output_language: 'ar',
  prompt_hint:
    'Focus on confidentiality under Saudi law, Arabic language requirements, and KSA jurisdiction clauses.',
};

// ---------------------------------------------------------------------------
// Playbook Catalog
// ---------------------------------------------------------------------------

/** All available contract review playbooks, grouped by region */
export const CONTRACT_PLAYBOOKS: ContractPlaybook[] = [
  // UAE
  UAE_PROCUREMENT_MSA,
  UAE_NDA,
  // KSA
  KSA_PROCUREMENT_MSA,
  KSA_NDA,
];

/** Get a playbook by ID */
export function getPlaybookById(id: string): ContractPlaybook | undefined {
  return CONTRACT_PLAYBOOKS.find(p => p.id === id);
}

/** Get playbooks grouped by region */
export function getPlaybooksByRegion(): Record<
  PlaybookRegion,
  ContractPlaybook[]
> {
  return {
    UAE: CONTRACT_PLAYBOOKS.filter(p => p.region === 'UAE'),
    KSA: CONTRACT_PLAYBOOKS.filter(p => p.region === 'KSA'),
  };
}
