import type { ReactNode } from 'react';
import {
  getCategoryMeta,
  getWorkflowById,
  type ToolRoute,
  type WorkflowCategory,
  type WorkflowDefinition,
} from '@/lib/workflowRegistry';
import type { OfficeDocType } from '@/lib/officeApi';

export const WORKFLOW_CATEGORY_ACCENTS: Record<WorkflowCategory, string> = {
  litigation: '#638cff',
  corporate: '#34d399',
  compliance: '#a78bfa',
  employment: '#fbbf24',
  arbitration: '#f472b6',
  enforcement: '#f97316',
  research: '#63b4ff',
  management: '#94a3b8',
};

export function getWorkflowCategoryHref(category: WorkflowCategory): string {
  return `/workflows/${category}`;
}

export function getWorkflowHref(workflow: WorkflowDefinition): string {
  return `${getWorkflowCategoryHref(workflow.category)}/${workflow.id}`;
}

export function getWorkflowLaunchHref(workflow: WorkflowDefinition): string {
  const params = new URLSearchParams({
    workflow: workflow.id,
    category: workflow.category,
  });

  return `${workflow.route}?${params.toString()}`;
}

export function getWorkflowDisplayName(
  workflow: WorkflowDefinition | undefined
): string {
  return workflow?.name || 'Workflow';
}

export function getCategoryDisplayName(category: WorkflowCategory): string {
  return getCategoryMeta(category)?.name || 'Workflow Category';
}

export function getToolLabel(route: ToolRoute): string {
  switch (route) {
    case '/documents':
      return 'Document Vault';
    case '/research':
      return 'Research';
    case '/contract-review':
      return 'Contract Review';
    case '/clause-redlines':
      return 'Clause Redlines';
    case '/conversations':
      return 'Conversations';
    case '/global-legal':
      return 'Global Legal Library';
    default:
      return 'Workspace';
  }
}

export function getWorkflowExecuteHref(workflow: WorkflowDefinition): string {
  return `${getWorkflowCategoryHref(workflow.category)}/${workflow.id}/execute`;
}

export const WORKFLOW_TEMPLATE_MAP: Record<
  string,
  { title: string; doc_type: OfficeDocType; template?: string }
> = {
  LITIGATION_CASE_FILING: { title: 'Statement of Claim', doc_type: 'docx', template: 'statement_of_claim' },
  LITIGATION_COURT_HEARINGS: { title: 'Hearing Memorandum', doc_type: 'docx', template: 'memorandum' },
  LITIGATION_EVIDENCE: { title: 'Evidence Bundle', doc_type: 'docx', template: 'evidence_bundle' },
  LITIGATION_APPEAL: { title: 'Appeal Memorandum', doc_type: 'docx', template: 'appeal_memorandum' },
  LITIGATION_GOVERNMENT: { title: 'Board of Grievances Filing', doc_type: 'docx', template: 'government_filing' },
  CORPORATE_FORMATION: { title: 'Articles of Association', doc_type: 'docx', template: 'articles_of_association' },
  CORPORATE_CONTRACTS: { title: 'Contract Draft', doc_type: 'docx', template: 'contract_draft' },
  CORPORATE_MA: { title: 'M&A Transaction Documents', doc_type: 'docx', template: 'ma_documents' },
  CORPORATE_FDI: { title: 'Investment Structure Memo', doc_type: 'docx', template: 'fdi_memo' },
  CORPORATE_GOVERNANCE: { title: 'Corporate Governance Report', doc_type: 'docx', template: 'governance_report' },
  COMPLIANCE_PRIVACY: { title: 'Privacy Compliance Report', doc_type: 'docx', template: 'privacy_report' },
  COMPLIANCE_AML: { title: 'AML Compliance Report', doc_type: 'docx', template: 'aml_report' },
  COMPLIANCE_SAUDIZATION: { title: 'Saudization Plan', doc_type: 'docx', template: 'saudization_plan' },
  COMPLIANCE_LICENSING: { title: 'License Application', doc_type: 'docx', template: 'license_application' },
  COMPLIANCE_ESG: { title: 'ESG Disclosure Report', doc_type: 'docx', template: 'esg_report' },
  EMPLOYMENT_DISPUTE: { title: 'Labor Dispute Filing', doc_type: 'docx', template: 'labor_dispute' },
  EMPLOYMENT_RESTRUCTURING: { title: 'Restructuring Plan', doc_type: 'docx', template: 'restructuring_plan' },
  EMPLOYMENT_CONTRACT: { title: 'Employment Contract', doc_type: 'docx', template: 'employment_contract' },
  EMPLOYMENT_COMPENSATION: { title: 'Compensation Analysis', doc_type: 'xlsx', template: 'compensation_analysis' },
  EMPLOYMENT_INVESTIGATION: { title: 'Investigation Report', doc_type: 'docx', template: 'investigation_report' },
  ARBITRATION_CLAUSE: { title: 'Arbitration Clause Draft', doc_type: 'docx', template: 'arbitration_clause' },
  ARBITRATION_CLAIMANT: { title: 'Statement of Claim (Arbitration)', doc_type: 'docx', template: 'arb_claim' },
  ARBITRATION_RESPONDENT: { title: 'Statement of Defence', doc_type: 'docx', template: 'arb_defence' },
  ARBITRATION_FOREIGN: { title: 'Foreign Judgment Recognition Filing', doc_type: 'docx', template: 'foreign_judgment' },
  ARBITRATION_MEDIATION: { title: 'Mediation Brief', doc_type: 'docx', template: 'mediation_brief' },
  ENFORCEMENT_PROMISSORY: { title: 'Promissory Note Filing', doc_type: 'docx', template: 'promissory_filing' },
  ENFORCEMENT_JUDGMENT: { title: 'Judgment Enforcement Application', doc_type: 'docx', template: 'judgment_enforcement' },
  ENFORCEMENT_DEBT: { title: 'Debt Recovery Filing', doc_type: 'docx', template: 'debt_recovery' },
  ENFORCEMENT_BANKRUPTCY: { title: 'Bankruptcy Filing', doc_type: 'docx', template: 'bankruptcy_filing' },
  ENFORCEMENT_CROSS_BORDER: { title: 'Cross-Border Enforcement Filing', doc_type: 'docx', template: 'cross_border_enforcement' },
  RESEARCH_LEGAL: { title: 'Legal Research Memo', doc_type: 'docx', template: 'research_memo' },
  RESEARCH_CASE_PREP: { title: 'Case Preparation Brief', doc_type: 'docx', template: 'case_prep' },
  RESEARCH_DUE_DILIGENCE: { title: 'Due Diligence Report', doc_type: 'docx', template: 'due_diligence_report' },
  RESEARCH_REGULATORY: { title: 'Regulatory Filing', doc_type: 'docx', template: 'regulatory_filing' },
  RESEARCH_CLIENT_COMMS: { title: 'Client Communication', doc_type: 'docx', template: 'client_letter' },
  MANAGEMENT_CLIENT_INTAKE: { title: 'Client Intake Form', doc_type: 'docx', template: 'client_intake' },
  MANAGEMENT_BILLING: { title: 'Billing Report', doc_type: 'xlsx', template: 'billing_report' },
  MANAGEMENT_FIRM_COMPLIANCE: { title: 'Firm Compliance Checklist', doc_type: 'docx', template: 'firm_compliance' },
  MANAGEMENT_BUSINESS_DEV: { title: 'Business Development Plan', doc_type: 'docx', template: 'business_dev' },
  MANAGEMENT_TALENT: { title: 'Talent Plan', doc_type: 'docx', template: 'talent_plan' },
};

export function getWorkflowFromSearchParam(
  workflowId: string | null
): WorkflowDefinition | undefined {
  if (!workflowId) return undefined;
  return getWorkflowById(workflowId);
}

export function renderCategoryIcon(
  category: WorkflowCategory,
  size: number = 22
): ReactNode {
  const props = {
    width: size,
    height: size,
    viewBox: '0 0 24 24',
    fill: 'none',
    stroke: 'currentColor',
    strokeWidth: 1.5,
  };

  switch (category) {
    case 'litigation':
      return (
        <svg {...props}>
          <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
        </svg>
      );
    case 'corporate':
      return (
        <svg {...props}>
          <rect x="2" y="7" width="20" height="14" rx="2" />
          <path d="M16 7V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v2" />
        </svg>
      );
    case 'compliance':
      return (
        <svg {...props}>
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
      );
    case 'employment':
      return (
        <svg {...props}>
          <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2" />
          <circle cx="9" cy="7" r="4" />
          <path d="M23 21v-2a4 4 0 0 0-3-3.87" />
          <path d="M16 3.13a4 4 0 0 1 0 7.75" />
        </svg>
      );
    case 'arbitration':
      return (
        <svg {...props}>
          <path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z" />
          <line x1="4" y1="22" x2="4" y2="15" />
        </svg>
      );
    case 'enforcement':
      return (
        <svg {...props}>
          <circle cx="12" cy="12" r="10" />
          <polyline points="12,6 12,12 16,14" />
        </svg>
      );
    case 'research':
      return (
        <svg {...props}>
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
        </svg>
      );
    case 'management':
      return (
        <svg {...props}>
          <path d="M12 20V10" />
          <path d="M18 20V4" />
          <path d="M6 20v-4" />
        </svg>
      );
    default:
      return null;
  }
}
