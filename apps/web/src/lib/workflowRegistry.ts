/**
 * KSA Law Firm Workflow Registry
 *
 * Defines all workflows available in the platform, organized by category
 * and tagged by persona. The sidebar reads from this registry and uses
 * twin/soul data + usage signals to compute a personalized ordering.
 *
 * Each workflow maps to one or more platform tools (routes) and contains
 * the granular steps a lawyer follows in KSA legal practice.
 */

// ============================================================================
// Types
// ============================================================================

export interface WorkflowStep {
  order: number;
  name: string;
  name_ar: string;
  detail: string;
  estimatedDuration?: string;
}

export type WorkflowSimulatedOutput =
  | {
      type: 'text' | 'document';
      content: string;
    }
  | {
      type: 'list';
      content: Array<{
        label: string;
        status: string;
        detail: string;
      }>;
    }
  | {
      type: 'score';
      score: number;
      label: string;
      items: string[];
    };

export interface WorkflowDefinition {
  id: string;
  name: string;
  name_ar: string;
  description: string;
  category: WorkflowCategory;
  persona_tags: PersonaTag[];
  steps: WorkflowStep[];
  /** Which platform tools this workflow primarily uses */
  tools: ToolRoute[];
  /** Default route when the user clicks this workflow */
  route: ToolRoute;
  icon: WorkflowIcon;
  estimatedDuration?: string;
}

export type WorkflowCategory =
  | 'litigation'
  | 'corporate'
  | 'compliance'
  | 'employment'
  | 'arbitration'
  | 'enforcement'
  | 'research'
  | 'management';

export type PersonaTag =
  | 'managing_partner'
  | 'litigation_advocate'
  | 'corporate_lawyer'
  | 'compliance_counsel'
  | 'employment_lawyer'
  | 'arbitration_counsel'
  | 'enforcement_lawyer'
  | 'junior_associate';

export type ToolRoute =
  | '/documents'
  | '/research'
  | '/contract-review'
  | '/clause-redlines'
  | '/conversations'
  | '/global-legal';

export type WorkflowIcon =
  | 'case-filing'
  | 'court'
  | 'evidence'
  | 'appeal'
  | 'government'
  | 'company'
  | 'contract'
  | 'merger'
  | 'investment'
  | 'governance'
  | 'privacy'
  | 'aml'
  | 'saudization'
  | 'license'
  | 'esg'
  | 'labor-dispute'
  | 'restructuring'
  | 'employment-contract'
  | 'compensation'
  | 'investigation'
  | 'arbitration-clause'
  | 'arbitration-claimant'
  | 'arbitration-respondent'
  | 'foreign-judgment'
  | 'mediation'
  | 'promissory'
  | 'judgment-enforce'
  | 'debt-recovery'
  | 'bankruptcy'
  | 'cross-border'
  | 'legal-research'
  | 'case-prep'
  | 'due-diligence'
  | 'regulatory-filing'
  | 'client-comms'
  | 'client-intake'
  | 'billing'
  | 'firm-compliance'
  | 'business-dev'
  | 'talent';

export interface WorkflowCategoryMeta {
  id: WorkflowCategory;
  name: string;
  name_ar: string;
}

// ============================================================================
// Category Metadata
// ============================================================================

export const WORKFLOW_CATEGORIES: WorkflowCategoryMeta[] = [
  { id: 'litigation', name: 'Litigation', name_ar: 'التقاضي' },
  {
    id: 'corporate',
    name: 'Corporate & Commercial',
    name_ar: 'الشركات والتجارة',
  },
  {
    id: 'compliance',
    name: 'Compliance & Regulatory',
    name_ar: 'الامتثال والتنظيم',
  },
  { id: 'employment', name: 'Employment & Labor', name_ar: 'العمل والعمال' },
  { id: 'arbitration', name: 'Dispute Resolution', name_ar: 'تسوية النزاعات' },
  {
    id: 'enforcement',
    name: 'Enforcement & Collection',
    name_ar: 'التنفيذ والتحصيل',
  },
  { id: 'research', name: 'Research & Support', name_ar: 'البحث والدعم' },
  { id: 'management', name: 'Firm Management', name_ar: 'إدارة المكتب' },
];

// ============================================================================
// Full Workflow Registry — 40 workflows across 8 personas
// ============================================================================

export const WORKFLOW_REGISTRY: WorkflowDefinition[] = [
  // --------------------------------------------------------------------------
  // LITIGATION (Persona: Litigation Advocate)
  // --------------------------------------------------------------------------
  {
    id: 'LITIGATION_CASE_FILING',
    name: 'Case Assessment & Filing',
    name_ar: 'تقييم القضية والتقديم',
    description:
      'Saudi courts use ~2,000 case types. Wrong classification triggers automatic dismissal. This workflow ensures correct Najiz filing.',
    category: 'litigation',
    persona_tags: ['litigation_advocate', 'junior_associate'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'case-filing',
    steps: [
      {
        order: 1,
        name: 'Client consultation & fact gathering',
        name_ar: 'استشارة العميل وجمع الحقائق',
        detail:
          'Collect contracts, correspondence, identity documents. Identify all parties with correct Arabic legal names.',
      },
      {
        order: 2,
        name: 'Legal analysis & strategy',
        name_ar: 'التحليل القانوني والاستراتيجية',
        detail:
          'Research applicable Saudi statutes, Royal Decrees, and judicial principles. Assess Sharia implications.',
      },
      {
        order: 3,
        name: 'Pre-litigation settlement',
        name_ar: 'التسوية قبل التقاضي',
        detail:
          'For labor: mandatory Amicable Settlement (21 days). For commercial: check arbitration clauses. Send formal demand (إنذار).',
      },
      {
        order: 4,
        name: 'Statement of Claim drafting',
        name_ar: 'صياغة صحيفة الدعوى',
        detail:
          'Draft per MOJ template in Arabic. Include parties, facts, legal basis, specific relief. Verify POA is active on Najiz.',
      },
      {
        order: 5,
        name: 'Electronic filing via Najiz',
        name_ar: 'التقديم الإلكتروني عبر ناجز',
        detail:
          'Select correct court and case classification. Upload claim and attachments. Pay fees. Receive case number.',
      },
    ],
  },
  {
    id: 'LITIGATION_COURT_HEARINGS',
    name: 'Court Hearings & Case Management',
    name_ar: 'الجلسات وإدارة القضايا',
    description:
      'Missing a virtual hearing or failing to submit a memorandum by deadline results in case dismissal under MOJ KPIs.',
    category: 'litigation',
    persona_tags: ['litigation_advocate'],
    tools: ['/documents', '/research', '/conversations'],
    route: '/documents',
    icon: 'court',
    steps: [
      {
        order: 1,
        name: 'Hearing preparation',
        name_ar: 'الإعداد للجلسة',
        detail:
          "Review case file, opposing submissions, judge's directions. Prepare memorandum with citations to Saudi statutes.",
      },
      {
        order: 2,
        name: 'Hearing attendance',
        name_ar: 'حضور الجلسة',
        detail:
          "Log into Najiz video system or attend physically. Present arguments. Record judge's questions and directions verbatim.",
      },
      {
        order: 3,
        name: 'Post-hearing memorandum',
        name_ar: 'المذكرة بعد الجلسة',
        detail:
          "Upload responsive memorandum within judge's deadline (3-10 days) via Najiz. Address all points raised.",
      },
      {
        order: 4,
        name: 'Witness & expert management',
        name_ar: 'إدارة الشهود والخبراء',
        detail:
          'File witness requests. Prepare witnesses for examination. Request court-appointed expert if needed.',
      },
      {
        order: 5,
        name: 'Status monitoring & reporting',
        name_ar: 'متابعة الحالة وإعداد التقارير',
        detail:
          'Monitor Najiz for updates. Send structured client reports after each hearing. Track deadlines in calendar.',
      },
    ],
  },
  {
    id: 'LITIGATION_EVIDENCE',
    name: 'Evidence Gathering & Presentation',
    name_ar: 'جمع وتقديم الأدلة',
    description:
      'The 2022 Law of Evidence modernized admissibility rules, including electronic evidence and WhatsApp messages.',
    category: 'litigation',
    persona_tags: ['litigation_advocate', 'junior_associate'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'evidence',
    steps: [
      {
        order: 1,
        name: 'Document collection & preservation',
        name_ar: 'جمع وحفظ المستندات',
        detail:
          'Issue preservation notices. Collect contracts, invoices, WhatsApp/email correspondence. Ensure metadata integrity.',
      },
      {
        order: 2,
        name: 'Electronic evidence authentication',
        name_ar: 'توثيق الأدلة الإلكترونية',
        detail:
          'Authenticate per Evidence Law: notarize screenshots via MOJ, obtain certified printouts, present through IT expert.',
      },
      {
        order: 3,
        name: 'Witness statement preparation',
        name_ar: 'إعداد شهادات الشهود',
        detail:
          'Draft statements in Arabic. Verify eligibility requirements. Prepare witnesses for cross-examination.',
      },
      {
        order: 4,
        name: 'Expert evidence coordination',
        name_ar: 'تنسيق أدلة الخبراء',
        detail:
          'Identify expert needs (financial, engineering, medical). File request with court. Review and challenge expert reports.',
      },
      {
        order: 5,
        name: 'Evidence submission & indexing',
        name_ar: 'تقديم وفهرسة الأدلة',
        detail:
          'Compile structured bundle per MOJ format. Upload via Najiz with Arabic descriptions. Ensure certified translations.',
      },
    ],
  },
  {
    id: 'LITIGATION_APPEAL',
    name: 'Appeal & Judicial Review',
    name_ar: 'الاستئناف والمراجعة القضائية',
    description:
      'Missing the 30-day appeal window forfeits the right entirely. Saudi three-tier system means most judgments pass through appeal.',
    category: 'litigation',
    persona_tags: ['litigation_advocate'],
    tools: ['/documents', '/research'],
    route: '/research',
    icon: 'appeal',
    steps: [
      {
        order: 1,
        name: 'Judgment analysis & assessment',
        name_ar: 'تحليل الحكم وتقييمه',
        detail:
          'Review full ruling including Sharia reasoning. Assess grounds: procedural errors, misapplication of law, factual errors.',
      },
      {
        order: 2,
        name: 'Appeal filing',
        name_ar: 'تقديم الاستئناف',
        detail:
          'File within 30 days via Najiz. Draft appeal memorandum specifying grounds, errors, and authorities.',
      },
      {
        order: 3,
        name: 'Appellate hearing preparation',
        name_ar: 'الإعداد لجلسة الاستئناف',
        detail:
          'Prepare supplementary memoranda focused on legal errors. Appellate courts may decide on papers only.',
      },
      {
        order: 4,
        name: 'Supreme Court petition',
        name_ar: 'طلب المحكمة العليا',
        detail:
          'Evaluate if Supreme Court review is available (discretionary). Draft petition for significant legal questions.',
      },
      {
        order: 5,
        name: 'Post-appeal implementation',
        name_ar: 'تنفيذ ما بعد الاستئناف',
        detail:
          'Obtain executable copy. Transition to enforcement if favorable. Advise on compliance if adverse.',
      },
    ],
  },
  {
    id: 'LITIGATION_BOG',
    name: 'Board of Grievances Proceedings',
    name_ar: 'إجراءات ديوان المظالم',
    description:
      'Disputes involving government entities — mega-project claims, procurement challenges, regulatory appeals — fall under the Board of Grievances.',
    category: 'litigation',
    persona_tags: ['litigation_advocate'],
    tools: ['/documents', '/research'],
    route: '/research',
    icon: 'government',
    steps: [
      {
        order: 1,
        name: 'Jurisdictional analysis',
        name_ar: 'تحليل الاختصاص',
        detail:
          'Determine Board jurisdiction: government contracts, administrative decisions, compensation claims. Identify correct court.',
      },
      {
        order: 2,
        name: 'Challenge preparation',
        name_ar: 'إعداد الطعن',
        detail:
          'Gather administrative decision, correspondence, evidence of notification date (triggers limitation period).',
      },
      {
        order: 3,
        name: 'Filing via Board portal',
        name_ar: 'التقديم عبر بوابة الديوان',
        detail:
          'File through Board of Grievances electronic portal per Board-specific template requirements.',
      },
      {
        order: 4,
        name: 'Interim relief applications',
        name_ar: 'طلبات الحماية المؤقتة',
        detail:
          'File for urgent suspension of administrative decision. Demonstrate prima facie case, urgency, irreparable harm.',
      },
      {
        order: 5,
        name: 'Government coordination',
        name_ar: 'التنسيق مع الجهات الحكومية',
        detail:
          'Manage service on government entity. Coordinate document exchange. Navigate longer government timelines.',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // CORPORATE & COMMERCIAL (Persona: Corporate Lawyer)
  // --------------------------------------------------------------------------
  {
    id: 'CORPORATE_FORMATION',
    name: 'Company Formation & Registration',
    name_ar: 'تأسيس وتسجيل الشركات',
    description:
      'End-to-end registration chain: MISA → MC → ZATCA → GOSI → Chamber → Bank. Each step has dependencies and timelines.',
    category: 'corporate',
    persona_tags: ['corporate_lawyer', 'junior_associate'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'company',
    steps: [
      {
        order: 1,
        name: 'Entity type selection',
        name_ar: 'اختيار نوع الكيان',
        detail:
          'Advise on LLC, JSC, branch, or representative office. Consider Saudization requirements per entity type.',
      },
      {
        order: 2,
        name: 'MISA license (foreign investors)',
        name_ar: 'ترخيص وزارة الاستثمار',
        detail:
          'Prepare application on investsaudi.sa. Submit parent company CR, board resolution, financials, UBO chart.',
      },
      {
        order: 3,
        name: 'Articles of Association',
        name_ar: 'عقد التأسيس',
        detail:
          'Draft in Arabic per Companies Law. Include shareholders, capital, management structure, profit distribution.',
      },
      {
        order: 4,
        name: 'Commercial Registration',
        name_ar: 'السجل التجاري',
        detail:
          'File on MC portal. Submit articles, shareholder IDs, Ejar-registered lease, ISIC activity codes.',
      },
      {
        order: 5,
        name: 'Post-incorporation registrations',
        name_ar: 'التسجيلات بعد التأسيس',
        detail:
          'Register with ZATCA, GOSI, Chamber of Commerce, WPS. Open corporate bank account.',
      },
    ],
  },
  {
    id: 'CORPORATE_CONTRACTS',
    name: 'Contract Drafting & Negotiation',
    name_ar: 'صياغة العقود والتفاوض',
    description:
      'The 2023 Civil Transactions Law codified contract principles. Arabic is the binding legal language.',
    category: 'corporate',
    persona_tags: ['corporate_lawyer', 'junior_associate'],
    tools: ['/contract-review', '/clause-redlines', '/documents'],
    route: '/contract-review',
    icon: 'contract',
    steps: [
      {
        order: 1,
        name: 'Scope & terms alignment',
        name_ar: 'تحديد النطاق والشروط',
        detail:
          'Identify key terms: price, payment, deliverables, warranties, liability caps. Determine governing law.',
      },
      {
        order: 2,
        name: 'First draft preparation',
        name_ar: 'إعداد المسودة الأولى',
        detail:
          'Draft in Arabic (controlling version). Prepare parallel English. Structure per Civil Transactions Law.',
      },
      {
        order: 3,
        name: 'Sharia & regulatory review',
        name_ar: 'المراجعة الشرعية والتنظيمية',
        detail:
          'Screen for Sharia compliance: no riba, no gharar. Check sector-specific regulations (CMA, SAMA, CITC).',
      },
      {
        order: 4,
        name: 'Negotiation & redlining',
        name_ar: 'التفاوض والتعديلات',
        detail:
          'Exchange drafts with counterparty. Track changes in bilingual versions. Ensure Arabic version is updated.',
      },
      {
        order: 5,
        name: 'Execution & notarization',
        name_ar: 'التوقيع والتوثيق',
        detail:
          'Arrange signing. For real estate/long-term leases: notarize through MOJ. File with relevant registry.',
      },
    ],
  },
  {
    id: 'CORPORATE_MA',
    name: 'M&A Transactions',
    name_ar: 'عمليات الاندماج والاستحواذ',
    description:
      'M&A surging in KSA — PIF restructuring, privatization, foreign investors. GAC competition clearance is critical-path.',
    category: 'corporate',
    persona_tags: ['corporate_lawyer'],
    tools: ['/documents', '/research', '/contract-review'],
    route: '/documents',
    icon: 'merger',
    steps: [
      {
        order: 1,
        name: 'Deal structuring & LOI',
        name_ar: 'هيكلة الصفقة وخطاب النوايا',
        detail:
          'Advise on share vs. asset purchase. Consider tax (20% WHT for non-residents). Draft LOI.',
      },
      {
        order: 2,
        name: 'Due diligence',
        name_ar: 'العناية الواجبة',
        detail:
          'Coordinate legal DD: corporate, regulatory, employment, real estate, contracts, litigation, IP, tax, environmental.',
      },
      {
        order: 3,
        name: 'Transaction documentation',
        name_ar: 'وثائق المعاملة',
        detail:
          'Draft SPA with price mechanism, representations, indemnities, conditions precedent, completion mechanics.',
      },
      {
        order: 4,
        name: 'Regulatory approvals',
        name_ar: 'الموافقات التنظيمية',
        detail:
          'File with GAC if thresholds met. Obtain sector approvals: SAMA, CMA, CITC. Ensure MISA approval for foreign acquirers.',
      },
      {
        order: 5,
        name: 'Closing & post-completion',
        name_ar: 'الإغلاق وما بعد الإتمام',
        detail:
          'Execute SPA, transfer shares via MC portal, update CR. Notify ZATCA, GOSI. Manage post-completion adjustments.',
      },
    ],
  },
  {
    id: 'CORPORATE_FDI',
    name: 'Foreign Investment Structuring',
    name_ar: 'هيكلة الاستثمار الأجنبي',
    description:
      '100% foreign ownership now allowed in most sectors. Structuring and regulatory pathway remains complex.',
    category: 'corporate',
    persona_tags: ['corporate_lawyer'],
    tools: ['/research', '/documents'],
    route: '/research',
    icon: 'investment',
    steps: [
      {
        order: 1,
        name: 'Feasibility analysis',
        name_ar: 'تحليل الجدوى',
        detail:
          'Review MISA negative list. Assess ownership caps. Model tax: 20% CIT for foreign-owned vs. 2.5% Zakat.',
      },
      {
        order: 2,
        name: 'Structuring advice',
        name_ar: 'الاستشارة الهيكلية',
        detail:
          'Recommend: 100% foreign LLC, JV, branch, or TSO. Advise on holding structure for treaty benefits.',
      },
      {
        order: 3,
        name: 'MISA license application',
        name_ar: 'طلب ترخيص وزارة الاستثمار',
        detail:
          'Prepare enhanced RHQ application for government contracting eligibility. Demonstrate management presence.',
      },
      {
        order: 4,
        name: 'Operational setup',
        name_ar: 'الإعداد التشغيلي',
        detail:
          'Coordinate: office lease (Ejar), municipality license, bank account, HR setup (Mudad, Qiwa), IT infrastructure.',
      },
      {
        order: 5,
        name: 'Ongoing compliance framework',
        name_ar: 'إطار الامتثال المستمر',
        detail:
          'Establish calendar: CR renewal, MISA renewal, ZATCA filings, GOSI, Nitaqat monitoring, PDPL compliance.',
      },
    ],
  },
  {
    id: 'CORPORATE_GOVERNANCE',
    name: 'Corporate Governance & Shareholder Matters',
    name_ar: 'حوكمة الشركات وشؤون المساهمين',
    description:
      'The 2022 Companies Law reformed governance. Non-compliance results in personal liability and forced liquidation.',
    category: 'corporate',
    persona_tags: ['corporate_lawyer', 'managing_partner'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'governance',
    steps: [
      {
        order: 1,
        name: 'Board/manager resolutions',
        name_ar: 'قرارات مجلس الإدارة',
        detail:
          'Draft resolutions for capital changes, officer appointments, related-party transactions. Maintain minute books.',
      },
      {
        order: 2,
        name: 'Shareholder meetings',
        name_ar: 'اجتماعات المساهمين',
        detail:
          'Prepare notices, agendas, proxy forms. For listed: comply with CMA/Tadawulaty. File minutes with MC.',
      },
      {
        order: 3,
        name: 'Capital restructuring',
        name_ar: 'إعادة هيكلة رأس المال',
        detail:
          'Advise on capital increases/reductions. Draft resolutions. Comply with 30-day creditor notification period.',
      },
      {
        order: 4,
        name: 'Related-party transactions',
        name_ar: 'معاملات الأطراف ذات العلاقة',
        detail:
          'Identify RPTs per Companies Law. Ensure disinterested approval. For listed: CMA RPT regulations.',
      },
      {
        order: 5,
        name: 'Annual compliance filings',
        name_ar: 'الإيداعات السنوية',
        detail:
          'File financials with MC. Appoint auditors. File Zakat/tax with ZATCA. Renew CR. Update UBO register.',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // COMPLIANCE & REGULATORY (Persona: Compliance Counsel)
  // --------------------------------------------------------------------------
  {
    id: 'COMPLIANCE_PDPL',
    name: 'PDPL Data Privacy Compliance',
    name_ar: 'الامتثال لنظام حماية البيانات الشخصية',
    description:
      'PDPL enforceable since Sep 2024. SDAIA has issued 48+ enforcement decisions. Fines up to SAR 5M, doubled for repeat violations.',
    category: 'compliance',
    persona_tags: ['compliance_counsel'],
    tools: ['/research', '/documents'],
    route: '/research',
    icon: 'privacy',
    steps: [
      {
        order: 1,
        name: 'Data mapping & inventory',
        name_ar: 'تخطيط البيانات والجرد',
        detail:
          'Catalog all personal data processing. Identify categories, purposes, legal bases, data flows, retention periods.',
      },
      {
        order: 2,
        name: 'Gap analysis',
        name_ar: 'تحليل الفجوات',
        detail:
          'Assess against PDPL: lawful basis, consent, privacy notices, DSAR processes, breach notification (72-hour).',
      },
      {
        order: 3,
        name: 'Policy & documentation',
        name_ar: 'السياسات والوثائق',
        detail:
          'Draft privacy policy (Arabic), internal DPP, DPA agreements, breach response plan, DPIA templates.',
      },
      {
        order: 4,
        name: 'NDGP registration & DPO',
        name_ar: 'التسجيل وتعيين مسؤول حماية البيانات',
        detail:
          'Determine NDGP registration requirement. File if triggered. Assess DPO appointment. Appoint Saudi representative.',
      },
      {
        order: 5,
        name: 'Ongoing monitoring',
        name_ar: 'المراقبة المستمرة',
        detail:
          'Establish compliance calendar. Monitor SDAIA decisions. Conduct breach exercises. Train staff annually.',
      },
    ],
  },
  {
    id: 'COMPLIANCE_AML',
    name: 'AML / Counter-Terrorism Financing',
    name_ar: 'مكافحة غسل الأموال وتمويل الإرهاب',
    description:
      'Law firms are designated non-financial businesses under Saudi AML Law. Non-compliance triggers criminal penalties.',
    category: 'compliance',
    persona_tags: ['compliance_counsel', 'managing_partner'],
    tools: ['/research', '/documents'],
    route: '/research',
    icon: 'aml',
    steps: [
      {
        order: 1,
        name: 'AML risk assessment',
        name_ar: 'تقييم مخاطر غسل الأموال',
        detail:
          'Conduct enterprise-wide assessment: customer risk, service risk, delivery channel risk, geographic risk.',
      },
      {
        order: 2,
        name: 'KYC/CDD program design',
        name_ar: 'تصميم برنامج اعرف عميلك',
        detail:
          'Design standard CDD, enhanced DD for PEPs, simplified DD for low-risk. Integrate with Absher/MC portals.',
      },
      {
        order: 3,
        name: 'Transaction monitoring & STR',
        name_ar: 'مراقبة المعاملات والإبلاغ',
        detail:
          'Implement monitoring for unusual patterns. File STRs with SAFIU via goAML portal. Maintain confidentiality.',
      },
      {
        order: 4,
        name: 'Sanctions screening',
        name_ar: 'فحص العقوبات',
        detail:
          'Screen against Saudi, UN, OFAC, EU sanctions lists. Implement ongoing screening. Establish escalation procedures.',
      },
      {
        order: 5,
        name: 'Training & record-keeping',
        name_ar: 'التدريب وحفظ السجلات',
        detail:
          'Annual AML training for all staff. Retain KYC records for 10 years. Prepare for regulatory inspections.',
      },
    ],
  },
  {
    id: 'COMPLIANCE_SAUDIZATION',
    name: 'Saudization & Labor Compliance',
    name_ar: 'السعودة والامتثال العمالي',
    description:
      'Nitaqat quotas determine hiring ability. 2025 amendments significantly increased penalties for non-compliance.',
    category: 'compliance',
    persona_tags: ['compliance_counsel', 'employment_lawyer'],
    tools: ['/research', '/documents'],
    route: '/research',
    icon: 'saudization',
    steps: [
      {
        order: 1,
        name: 'Nitaqat ratio analysis',
        name_ar: 'تحليل نسبة نطاقات',
        detail:
          'Access Qiwa portal. Calculate current ratio against sector thresholds. Identify band (Red to Platinum).',
      },
      {
        order: 2,
        name: 'Remediation planning',
        name_ar: 'خطة المعالجة',
        detail:
          'Develop hiring plan. Identify roles for Saudi nationals via Taqat. Calculate cost impact.',
      },
      {
        order: 3,
        name: 'Contract standardization',
        name_ar: 'توحيد العقود',
        detail:
          'Review all contracts against 2025 Labor Law amendments. Ensure mandatory clauses. Standardize in Arabic.',
      },
      {
        order: 4,
        name: 'GOSI & WPS compliance',
        name_ar: 'الامتثال للتأمينات والحماية',
        detail:
          'Verify all employees registered on GOSI. Ensure payroll through WPS via Mudad. Reconcile monthly.',
      },
      {
        order: 5,
        name: 'Workplace policy compliance',
        name_ar: 'امتثال سياسات مكان العمل',
        detail:
          'Draft internal work regulations (50+ employees). Anti-harassment policy. Health & safety. File with HRSD.',
      },
    ],
  },
  {
    id: 'COMPLIANCE_LICENSING',
    name: 'Sector-Specific Regulatory Licensing',
    name_ar: 'التراخيص التنظيمية القطاعية',
    description:
      'Most business activities require sector-specific licenses. Operating without the correct license is criminal.',
    category: 'compliance',
    persona_tags: ['compliance_counsel', 'corporate_lawyer'],
    tools: ['/research', '/documents'],
    route: '/research',
    icon: 'license',
    steps: [
      {
        order: 1,
        name: 'Regulatory mapping',
        name_ar: 'تخطيط الجهات التنظيمية',
        detail:
          'Identify all required approvals: SAMA, CMA, CITC, SFDA, NCEA, TGA, GEA, municipality licenses.',
      },
      {
        order: 2,
        name: 'Application preparation',
        name_ar: 'إعداد الطلب',
        detail:
          'Gather entity documents, feasibility studies, business plans, key personnel qualifications.',
      },
      {
        order: 3,
        name: 'Submission & engagement',
        name_ar: 'التقديم والتواصل',
        detail:
          'Submit through regulator portals. Manage queries. For fintech: prepare SAMA sandbox application.',
      },
      {
        order: 4,
        name: 'Condition compliance',
        name_ar: 'الامتثال للشروط',
        detail:
          'Implement license conditions: capital deployment, staffing, systems, insurance. Coordinate inspections.',
      },
      {
        order: 5,
        name: 'Ongoing reporting',
        name_ar: 'التقارير المستمرة',
        detail:
          'Establish reporting calendar per regulator. Monitor circulars. Manage renewals. Handle inspections.',
      },
    ],
  },
  {
    id: 'COMPLIANCE_ESG',
    name: 'ESG & Environmental Compliance',
    name_ar: 'الامتثال البيئي والاجتماعي والحوكمة',
    description:
      'Saudi Green Initiative, NEOM sustainability requirements, and Tadawul ESG disclosure rules create new compliance frontiers.',
    category: 'compliance',
    persona_tags: ['compliance_counsel'],
    tools: ['/research', '/documents'],
    route: '/research',
    icon: 'esg',
    steps: [
      {
        order: 1,
        name: 'ESG landscape assessment',
        name_ar: 'تقييم المشهد البيئي',
        detail:
          'Map: NCEC permits, CMA ESG guidelines, Saudi Green Initiative targets, contractual ESG requirements.',
      },
      {
        order: 2,
        name: 'Environmental compliance',
        name_ar: 'الامتثال البيئي',
        detail:
          'Obtain NCEC permits. Prepare EIAs. Monitor emissions. Manage hazardous waste disposal.',
      },
      {
        order: 3,
        name: 'Health & safety program',
        name_ar: 'برنامج الصحة والسلامة',
        detail:
          'Ensure Labor Law compliance. Draft safety manuals. For construction: Saudi Building Code requirements.',
      },
      {
        order: 4,
        name: 'ESG reporting',
        name_ar: 'تقارير الاستدامة',
        detail:
          'For listed companies: annual ESG disclosures per CMA/Tadawul. For mega-projects: contractual ESG reports.',
      },
      {
        order: 5,
        name: 'Carbon & sustainability',
        name_ar: 'الكربون والاستدامة',
        detail:
          'Advise on carbon credit market. Monitor Green Initiative policy. Advise on renewable energy obligations.',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // EMPLOYMENT & LABOR (Persona: Employment Lawyer)
  // --------------------------------------------------------------------------
  {
    id: 'EMPLOYMENT_DISPUTES',
    name: 'Labor Dispute Resolution',
    name_ar: 'تسوية النزاعات العمالية',
    description:
      'Mandatory Amicable Settlement phase is required before court. Judges apply Labor Law strictly.',
    category: 'employment',
    persona_tags: ['employment_lawyer', 'litigation_advocate'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'labor-dispute',
    steps: [
      {
        order: 1,
        name: 'Dispute intake & assessment',
        name_ar: 'استقبال النزاع وتقييمه',
        detail:
          'Gather employment docs: contract, WPS printouts, GOSI records, disciplinary file. Calculate ESB exposure.',
      },
      {
        order: 2,
        name: 'Amicable Settlement filing',
        name_ar: 'تقديم التسوية الودية',
        detail:
          'File on HRSD Wedd platform. Upload claim details and documents. Attend virtual settlement within 21 days.',
      },
      {
        order: 3,
        name: 'Settlement negotiation',
        name_ar: 'التفاوض على التسوية',
        detail:
          'Negotiate within statutory ESB to full compensation range. Document agreement per HRSD template.',
      },
      {
        order: 4,
        name: 'Labor court litigation',
        name_ar: 'التقاضي أمام المحكمة العمالية',
        detail:
          'Auto-transfer via Najiz upon non-reconciliation. File claim with specific monetary amounts. Cases conclude in 3-6 months.',
      },
      {
        order: 5,
        name: 'Judgment enforcement',
        name_ar: 'تنفيذ الحكم',
        detail:
          'File enforcement request via Najiz. For employers: advise on payment timeline to avoid travel bans and bank freezes.',
      },
    ],
  },
  {
    id: 'EMPLOYMENT_RESTRUCTURING',
    name: 'Workforce Restructuring',
    name_ar: 'إعادة هيكلة القوى العاملة',
    description:
      'Mass layoffs are politically sensitive in KSA. Saudization implications must be modeled before execution.',
    category: 'employment',
    persona_tags: ['employment_lawyer', 'managing_partner'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'restructuring',
    steps: [
      {
        order: 1,
        name: 'Strategy & planning',
        name_ar: 'الاستراتيجية والتخطيط',
        detail:
          'Model Nitaqat impact. Identify affected positions. Assess contractual termination provisions.',
      },
      {
        order: 2,
        name: 'Legal risk assessment',
        name_ar: 'تقييم المخاطر القانونية',
        detail:
          'Calculate ESB liability per employee. Identify protected categories: pregnant women, sick leave, Saudis.',
      },
      {
        order: 3,
        name: 'HRSD notification',
        name_ar: 'إخطار وزارة الموارد البشرية',
        detail:
          'Notify HRSD for large-scale redundancies. Coordinate Iqama cancellation timeline (60 days).',
      },
      {
        order: 4,
        name: 'Termination execution',
        name_ar: 'تنفيذ الإنهاء',
        detail:
          'Prepare termination letters (Arabic, specifying legal basis). Conduct exit meetings. Obtain signed settlements.',
      },
      {
        order: 5,
        name: 'Post-restructuring compliance',
        name_ar: 'الامتثال بعد إعادة الهيكلة',
        detail:
          'Process GOSI de-registrations. Final WPS payments. Cancel Iqamas. Monitor for claims (12-month limitation).',
      },
    ],
  },
  {
    id: 'EMPLOYMENT_CONTRACTS',
    name: 'Employment Contract & Policy Drafting',
    name_ar: 'صياغة عقود وسياسات العمل',
    description:
      'Saudi Labor Law mandates specific contract terms. 2025 amendments require contract updates across workforces.',
    category: 'employment',
    persona_tags: ['employment_lawyer', 'junior_associate'],
    tools: ['/contract-review', '/clause-redlines', '/documents'],
    route: '/contract-review',
    icon: 'employment-contract',
    steps: [
      {
        order: 1,
        name: 'Template development',
        name_ar: 'تطوير النماذج',
        detail:
          'Draft templates for: Saudi permanent, fixed-term, foreign, part-time, remote workers. Arabic controlling.',
      },
      {
        order: 2,
        name: 'Mandatory terms check',
        name_ar: 'فحص الشروط الإلزامية',
        detail:
          'Verify: probation (90/180 days), hours (8/48; 6/36 Ramadan), leave (21/30 days), ESB provisions.',
      },
      {
        order: 3,
        name: 'Restrictive covenants',
        name_ar: 'شروط عدم المنافسة',
        detail:
          'Draft non-competes (max 2 years, limited scope/geography). Non-solicitation. Confidentiality obligations.',
      },
      {
        order: 4,
        name: 'Internal work regulations',
        name_ar: 'لائحة تنظيم العمل',
        detail:
          'For 50+ employees: draft comprehensive regulations. File with HRSD for approval.',
      },
      {
        order: 5,
        name: 'HR policy suite',
        name_ar: 'مجموعة سياسات الموارد البشرية',
        detail:
          'Draft: anti-harassment (mandatory), whistleblower, PDPL employee notice, remote work, performance management.',
      },
    ],
  },
  {
    id: 'EMPLOYMENT_COMPENSATION',
    name: 'Executive Compensation & Benefits',
    name_ar: 'التعويضات والمزايا التنفيذية',
    description:
      'No personal income tax in KSA, but structuring around GOSI, housing allowances, and equity requires careful design.',
    category: 'employment',
    persona_tags: ['employment_lawyer', 'corporate_lawyer'],
    tools: ['/research', '/documents'],
    route: '/research',
    icon: 'compensation',
    steps: [
      {
        order: 1,
        name: 'Compensation design',
        name_ar: 'تصميم التعويضات',
        detail:
          'Benchmark against KSA market. Design: base salary, housing (25%, included in ESB), transportation, bonus.',
      },
      {
        order: 2,
        name: 'GOSI optimization',
        name_ar: 'تحسين التأمينات الاجتماعية',
        detail:
          'Structure around GOSI cap (SAR 45,000/month). Advise on which allowances are contributory.',
      },
      {
        order: 3,
        name: 'Equity incentives',
        name_ar: 'الحوافز في الأسهم',
        detail:
          'Design phantom shares/SARs for non-listed. Share options for listed (CMA regulated). Vesting, leaver provisions.',
      },
      {
        order: 4,
        name: 'Expatriate packages',
        name_ar: 'حزم الموظفين الأجانب',
        detail:
          'Design: relocation, schooling, air tickets (mandatory), CCHI medical insurance, Iqama/family visa costs.',
      },
      {
        order: 5,
        name: 'Severance negotiation',
        name_ar: 'التفاوض على مكافأة نهاية الخدمة',
        detail:
          'Draft enhanced ESB provisions, garden leave, accelerated vesting, settlement agreements with mutual release.',
      },
    ],
  },
  {
    id: 'EMPLOYMENT_INVESTIGATIONS',
    name: 'Workplace Investigations',
    name_ar: 'التحقيقات في مكان العمل',
    description:
      'Anti-Harassment Law mandates employer investigation of complaints. Failure creates employer liability.',
    category: 'employment',
    persona_tags: ['employment_lawyer'],
    tools: ['/documents', '/conversations'],
    route: '/documents',
    icon: 'investigation',
    steps: [
      {
        order: 1,
        name: 'Complaint receipt & assessment',
        name_ar: 'استلام الشكوى وتقييمها',
        detail:
          'Assess nature: harassment, misconduct, policy violation. Determine need for immediate protective measures.',
      },
      {
        order: 2,
        name: 'Investigation planning',
        name_ar: 'تخطيط التحقيق',
        detail:
          'Appoint investigator. Draft plan: scope, witnesses, documents, timeline. Address PDPL implications.',
      },
      {
        order: 3,
        name: 'Interviews & evidence',
        name_ar: 'المقابلات والأدلة',
        detail:
          'Interview complainant, respondent, witnesses. Document in Arabic (signed). Collect electronic evidence.',
      },
      {
        order: 4,
        name: 'Findings & discipline',
        name_ar: 'النتائج والإجراءات التأديبية',
        detail:
          'Prepare report. Recommend action per Article 66 schedule. For Article 80 dismissal: ensure heightened evidence.',
      },
      {
        order: 5,
        name: 'Resolution & remediation',
        name_ar: 'الحل والمعالجة',
        detail:
          'Implement decision. Report to police if criminal. Support complainant. Systemic remediation.',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // DISPUTE RESOLUTION (Persona: Arbitration Counsel)
  // --------------------------------------------------------------------------
  {
    id: 'ARBITRATION_CLAUSE',
    name: 'Arbitration Clause Drafting',
    name_ar: 'صياغة شرط التحكيم',
    description:
      'A poorly drafted clause is the most common source of jurisdictional challenges in Saudi arbitration.',
    category: 'arbitration',
    persona_tags: ['arbitration_counsel', 'corporate_lawyer'],
    tools: ['/clause-redlines', '/contract-review'],
    route: '/clause-redlines',
    icon: 'arbitration-clause',
    steps: [
      {
        order: 1,
        name: 'Mechanism selection',
        name_ar: 'اختيار الآلية',
        detail:
          'Advise on: SCCA arbitration, ad hoc, ICC/LCIA, or multi-tiered clause. Consider enforceability.',
      },
      {
        order: 2,
        name: 'Clause drafting',
        name_ar: 'صياغة الشرط',
        detail:
          'Draft with precision: institution (SCCA), rules (2023), seat, number of arbitrators, language, governing law.',
      },
      {
        order: 3,
        name: 'Multi-tiered design',
        name_ar: 'التصميم متعدد المراحل',
        detail:
          'Draft escalation: negotiation → SCCA mediation → arbitration. Define condition precedent language.',
      },
      {
        order: 4,
        name: 'Governing law analysis',
        name_ar: 'تحليل القانون الحاكم',
        detail:
          'Advise on law selection. Saudi law mandatory for certain contracts. Consider Sharia compliance for enforcement.',
      },
      {
        order: 5,
        name: 'Dispute avoidance mechanisms',
        name_ar: 'آليات تفادي النزاعات',
        detail:
          'Draft: notice and cure, expert determination, dispute review boards, price adjustment mechanisms.',
      },
    ],
  },
  {
    id: 'ARBITRATION_CLAIMANT',
    name: 'Arbitration (Claimant)',
    name_ar: 'التحكيم (المدعي)',
    description:
      'SCCA arbitration is the preferred forum for high-value KSA commercial disputes. 2023 rules introduced early disposition.',
    category: 'arbitration',
    persona_tags: ['arbitration_counsel', 'litigation_advocate'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'arbitration-claimant',
    steps: [
      {
        order: 1,
        name: 'Pre-arbitration notice',
        name_ar: 'الإخطار قبل التحكيم',
        detail:
          'Issue formal dispute notice. Comply with multi-tiered pre-conditions. Document compliance.',
      },
      {
        order: 2,
        name: 'Request for Arbitration',
        name_ar: 'طلب التحكيم',
        detail:
          'File with SCCA: parties, dispute, clause, claims, relief, arbitrator count. Pay SAR 2,000 registration fee.',
      },
      {
        order: 3,
        name: 'Tribunal constitution',
        name_ar: 'تشكيل هيئة التحكيم',
        detail:
          'Nominate arbitrators based on expertise, language, nationality. Participate in procedural conference.',
      },
      {
        order: 4,
        name: 'Memorial & hearing',
        name_ar: 'المذكرة والجلسة',
        detail:
          'Draft Statement of Claim with legal analysis, quantum. Submit witness/expert reports. Attend oral hearing.',
      },
      {
        order: 5,
        name: 'Award enforcement',
        name_ar: 'تنفيذ الحكم',
        detail:
          'File for enforcement via Najiz or under New York Convention. Challenge adverse awards within 60 days.',
      },
    ],
  },
  {
    id: 'ARBITRATION_RESPONDENT',
    name: 'Arbitration (Respondent)',
    name_ar: 'التحكيم (المدعى عليه)',
    description:
      'Defense strategy including jurisdictional challenges, counterclaims, and security for costs.',
    category: 'arbitration',
    persona_tags: ['arbitration_counsel', 'litigation_advocate'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'arbitration-respondent',
    steps: [
      {
        order: 1,
        name: 'Response strategy',
        name_ar: 'استراتيجية الرد',
        detail:
          'Assess: validity of agreement, merits of claim, counterclaim potential. Consider jurisdictional objection.',
      },
      {
        order: 2,
        name: 'Answer & counterclaim',
        name_ar: 'الرد والدعوى المضادة',
        detail:
          'File Answer within 30 days. Include jurisdictional objections, defense, counterclaims, arbitrator nomination.',
      },
      {
        order: 3,
        name: 'Procedural strategy',
        name_ar: 'الاستراتيجية الإجرائية',
        detail:
          'Advocate for document production scope, witness sequence, expert process. Request security for costs.',
      },
      {
        order: 4,
        name: 'Defense memorial & hearing',
        name_ar: 'مذكرة الدفاع والجلسة',
        detail:
          'Draft counter-memorial. Present defenses: limitation, waiver, force majeure. Cross-examine claimant witnesses.',
      },
      {
        order: 5,
        name: 'Award challenge',
        name_ar: 'الطعن في الحكم',
        detail:
          'Assess annulment grounds under Article 50. File within 60 days. Enforce counterclaim award if successful.',
      },
    ],
  },
  {
    id: 'ARBITRATION_FOREIGN_ENFORCEMENT',
    name: 'Foreign Judgment & Award Enforcement',
    name_ar: 'تنفيذ الأحكام والقرارات الأجنبية',
    description:
      'Saudi courts apply New York Convention for arbitral awards. Foreign court judgments have more limited frameworks.',
    category: 'arbitration',
    persona_tags: ['arbitration_counsel', 'enforcement_lawyer'],
    tools: ['/documents', '/research'],
    route: '/research',
    icon: 'foreign-judgment',
    steps: [
      {
        order: 1,
        name: 'Enforceability assessment',
        name_ar: 'تقييم قابلية التنفيذ',
        detail:
          'Determine: New York Convention (arbitral awards) or bilateral treaty (judgments). Assess Sharia compliance risks.',
      },
      {
        order: 2,
        name: 'Document preparation',
        name_ar: 'إعداد المستندات',
        detail:
          'Obtain certified copies, Arabic translations, proof of service, proof of finality. Apostille all documents.',
      },
      {
        order: 3,
        name: 'Enforcement application',
        name_ar: 'طلب التنفيذ',
        detail:
          'For awards: file with Court of Appeal per Article 55. For judgments: file with General Court or Board of Grievances.',
      },
      {
        order: 4,
        name: 'Opposing challenges',
        name_ar: 'مواجهة الاعتراضات',
        detail:
          'Prepare for objections: public policy (most common — riba/interest provisions), lack of jurisdiction, invalid service.',
      },
      {
        order: 5,
        name: 'Execution of enforced award',
        name_ar: 'تنفيذ الحكم المعترف به',
        detail:
          'File with Execution Court via Najiz. Apply for enforcement measures: bank freezes, asset seizure, travel bans.',
      },
    ],
  },
  {
    id: 'ARBITRATION_MEDIATION',
    name: 'Mediation & ADR',
    name_ar: 'الوساطة وتسوية النزاعات البديلة',
    description:
      'Courts increasingly encourage mediation. Successful mediation preserves business relationships.',
    category: 'arbitration',
    persona_tags: ['arbitration_counsel'],
    tools: ['/documents', '/conversations'],
    route: '/conversations',
    icon: 'mediation',
    steps: [
      {
        order: 1,
        name: 'Suitability assessment',
        name_ar: 'تقييم الملاءمة',
        detail:
          'Evaluate: ongoing relationship, complexity, emotional temperature, power imbalance, need for precedent.',
      },
      {
        order: 2,
        name: 'Mediator selection',
        name_ar: 'اختيار الوسيط',
        detail:
          'Select from SCCA panel or Saudi Commercial Mediation Center. Agree on protocol and costs allocation.',
      },
      {
        order: 3,
        name: 'Preparation',
        name_ar: 'الإعداد',
        detail:
          'Prepare position paper. Develop BATNA analysis. Identify interests and red lines. Coach client.',
      },
      {
        order: 4,
        name: 'Session participation',
        name_ar: 'المشاركة في الجلسة',
        detail:
          'Attend sessions (1-2 days). Joint sessions and private caucuses. Draft heads of terms on-site if breakthrough.',
      },
      {
        order: 5,
        name: 'Settlement execution',
        name_ar: 'تنفيذ التسوية',
        detail:
          'Draft settlement in Arabic. SCCA-endorsed agreements enforceable as court judgments. Register with court.',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // ENFORCEMENT & COLLECTION (Persona: Enforcement Lawyer)
  // --------------------------------------------------------------------------
  {
    id: 'ENFORCEMENT_PROMISSORY',
    name: 'Promissory Note Enforcement',
    name_ar: 'تنفيذ السند لأمر',
    description:
      'Promissory notes are directly enforceable without litigation — the most common enforcement instrument in Saudi commerce.',
    category: 'enforcement',
    persona_tags: ['enforcement_lawyer'],
    tools: ['/documents'],
    route: '/documents',
    icon: 'promissory',
    steps: [
      {
        order: 1,
        name: 'Instrument verification',
        name_ar: 'التحقق من السند',
        detail:
          'Verify formal requirements: unconditional promise, fixed amount, maturity date, payee, signature. Check 3-year limitation.',
      },
      {
        order: 2,
        name: 'Filing via Najiz',
        name_ar: 'التقديم عبر ناجز',
        detail:
          'File execution request on Najiz Enforcement Court. Upload original note, creditor ID, debtor details. Pay fees.',
      },
      {
        order: 3,
        name: 'Debtor notification',
        name_ar: 'إخطار المدين',
        detail:
          'Court issues 5-day payment notice via Najiz/SMS. If debtor objects: referred to court for adjudication.',
      },
      {
        order: 4,
        name: 'Enforcement escalation',
        name_ar: 'تصعيد التنفيذ',
        detail:
          'Request: bank freeze (SAMA integration), travel ban, vehicle seizure, real estate attachment, Simah listing.',
      },
      {
        order: 5,
        name: 'Asset realization',
        name_ar: 'تحصيل الأصول',
        detail:
          'Coordinate auction process. For bank balances: direct transfer. Collect proceeds and close enforcement file.',
      },
    ],
  },
  {
    id: 'ENFORCEMENT_JUDGMENT',
    name: 'Judgment Enforcement',
    name_ar: 'تنفيذ الأحكام القضائية',
    description:
      'Winning a judgment is half the battle — collection requires separate enforcement process with powerful tools.',
    category: 'enforcement',
    persona_tags: ['enforcement_lawyer', 'litigation_advocate'],
    tools: ['/documents'],
    route: '/documents',
    icon: 'judgment-enforce',
    steps: [
      {
        order: 1,
        name: 'Executable copy',
        name_ar: 'الصورة التنفيذية',
        detail:
          'Obtain executable copy from issuing court via Najiz after judgment becomes final.',
      },
      {
        order: 2,
        name: 'Enforcement application',
        name_ar: 'طلب التنفيذ',
        detail:
          "File on Najiz with Enforcement Court in debtor's jurisdiction. Attach executable copy and debtor information.",
      },
      {
        order: 3,
        name: 'Asset investigation',
        name_ar: 'التحري عن الأصول',
        detail:
          'Request disclosure orders: SAMA bank circular, MOJ real estate query, traffic department, MC business interests.',
      },
      {
        order: 4,
        name: 'Enforcement measures',
        name_ar: 'إجراءات التنفيذ',
        detail:
          'Bank seizure, real estate forced sale, vehicle seizure, stock freeze (CMA/Tadawul). Travel ban for individuals.',
      },
      {
        order: 5,
        name: 'Payment management & closure',
        name_ar: 'إدارة المدفوعات والإغلاق',
        detail:
          'Track partial payments. Negotiate installments. Upon full satisfaction: lift measures and close file.',
      },
    ],
  },
  {
    id: 'ENFORCEMENT_PRE_LITIGATION',
    name: 'Pre-Litigation Debt Recovery',
    name_ar: 'تحصيل الديون قبل التقاضي',
    description:
      'Most debts can be recovered without litigation. The formal demand letter carries significant weight in KSA.',
    category: 'enforcement',
    persona_tags: ['enforcement_lawyer', 'junior_associate'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'debt-recovery',
    steps: [
      {
        order: 1,
        name: 'Debt verification',
        name_ar: 'التحقق من الدين',
        detail:
          'Review contracts, invoices, delivery confirmations. Verify debt is due. Calculate total: principal + penalties.',
      },
      {
        order: 2,
        name: 'Formal demand letter',
        name_ar: 'الإنذار الرسمي',
        detail:
          'Draft in Arabic. Deliver via registered mail, MOJ notary, or Najiz notification. Include deadline and consequences.',
      },
      {
        order: 3,
        name: 'Settlement negotiation',
        name_ar: 'التفاوض على التسوية',
        detail:
          'Negotiate discount for immediate payment (5-15%). Draft payment plan with post-dated promissory notes.',
      },
      {
        order: 4,
        name: 'Escalation decision',
        name_ar: 'قرار التصعيد',
        detail:
          'For promissory notes: direct enforcement. For contracts: file with Commercial Court. Under SAR 500K: SCCA ODR.',
      },
      {
        order: 5,
        name: 'Commercial pressure',
        name_ar: 'الضغط التجاري',
        detail:
          'Report to Simah credit bureau. For bounced checks: file criminal complaint. These often prompt payment.',
      },
    ],
  },
  {
    id: 'ENFORCEMENT_BANKRUPTCY',
    name: 'Bankruptcy & Insolvency',
    name_ar: 'الإفلاس والإعسار',
    description:
      'Saudi Bankruptcy Law (2018) introduced protective settlement, financial restructuring, and liquidation procedures.',
    category: 'enforcement',
    persona_tags: ['enforcement_lawyer', 'corporate_lawyer'],
    tools: ['/documents', '/research'],
    route: '/research',
    icon: 'bankruptcy',
    steps: [
      {
        order: 1,
        name: 'Insolvency assessment',
        name_ar: 'تقييم الإعسار',
        detail:
          'Evaluate: balance-sheet insolvency or cash-flow insolvency. Assess whether involuntary petition is strategic.',
      },
      {
        order: 2,
        name: 'Procedure selection',
        name_ar: 'اختيار الإجراء',
        detail:
          'Advise on: protective settlement, financial restructuring, or liquidation. Each has different requirements.',
      },
      {
        order: 3,
        name: 'Application filing',
        name_ar: 'تقديم الطلب',
        detail:
          'File with Commercial Court. Submit financials, creditor list, restructuring plan. Court appoints bankruptcy trustee.',
      },
      {
        order: 4,
        name: 'Creditor claims & voting',
        name_ar: 'مطالبات الدائنين والتصويت',
        detail:
          'File proof of debt. Verify claims. Participate in creditor committee. Vote on restructuring plan.',
      },
      {
        order: 5,
        name: 'Plan implementation',
        name_ar: 'تنفيذ الخطة',
        detail:
          'Monitor compliance with plan. For liquidation: assert priority claims per Bankruptcy Law waterfall.',
      },
    ],
  },
  {
    id: 'ENFORCEMENT_CROSS_BORDER',
    name: 'Cross-Border Debt Recovery',
    name_ar: 'تحصيل الديون عبر الحدود',
    description:
      "KSA's largest-economy status means significant cross-border commerce. Recovery requires navigating international frameworks.",
    category: 'enforcement',
    persona_tags: ['enforcement_lawyer', 'arbitration_counsel'],
    tools: ['/documents', '/research'],
    route: '/research',
    icon: 'cross-border',
    steps: [
      {
        order: 1,
        name: 'Jurisdiction analysis',
        name_ar: 'تحليل الاختصاص',
        detail:
          'Determine asset locations. Assess bilateral treaties. Evaluate enforcement frameworks in target jurisdictions.',
      },
      {
        order: 2,
        name: 'International service',
        name_ar: 'التبليغ الدولي',
        detail:
          'Effect service per Riyadh Convention, bilateral treaties, or diplomatic channels via MOFA.',
      },
      {
        order: 3,
        name: 'Foreign asset tracing',
        name_ar: 'تتبع الأصول الأجنبية',
        detail:
          'Engage local counsel. Trace: bank accounts, real estate, corporate interests. Coordinate multi-jurisdictional freezes.',
      },
      {
        order: 4,
        name: 'Parallel enforcement',
        name_ar: 'التنفيذ المتوازي',
        detail:
          'File Saudi judgment/award in each jurisdiction. Manage anti-suit injunction risks. Prevent double-recovery.',
      },
      {
        order: 5,
        name: 'Recovery & repatriation',
        name_ar: 'التحصيل وتحويل الأموال',
        detail:
          'Arrange fund repatriation. Comply with SAMA forex regulations. Account for foreign counsel fees.',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // RESEARCH & SUPPORT (Persona: Junior Associate)
  // --------------------------------------------------------------------------
  {
    id: 'RESEARCH_LEGAL_MEMO',
    name: 'Legal Research & Memoranda',
    name_ar: 'البحث القانوني والمذكرات',
    description:
      'Saudi legal research is challenging: many principles unpublished, codification recent, Sharia reasoning requires specialist knowledge.',
    category: 'research',
    persona_tags: ['junior_associate', 'litigation_advocate'],
    tools: ['/research', '/global-legal'],
    route: '/research',
    icon: 'legal-research',
    steps: [
      {
        order: 1,
        name: 'Research request intake',
        name_ar: 'استقبال طلب البحث',
        detail:
          'Clarify: legal question, jurisdiction, relevant facts, deadline, output format (memo, advice, submission).',
      },
      {
        order: 2,
        name: 'Primary source research',
        name_ar: 'البحث في المصادر الأولية',
        detail:
          'Search: Royal Decrees (boe.gov.sa), judicial principles, MOJ judgments, regulatory circulars, ratified treaties.',
      },
      {
        order: 3,
        name: 'Secondary & comparative',
        name_ar: 'المصادر الثانوية والمقارنة',
        detail:
          'Consult Saudi commentaries, Sharia treatises, international publications, GCC comparative analysis.',
      },
      {
        order: 4,
        name: 'Memorandum drafting',
        name_ar: 'صياغة المذكرة',
        detail:
          'Structure: Question, Short Answer, Facts, Legal Analysis (statute-by-statute with Sharia context), Conclusion.',
      },
      {
        order: 5,
        name: 'Quality review & KM',
        name_ar: 'المراجعة وإدارة المعرفة',
        detail:
          'Submit for partner review. File in knowledge management system with tags. Update precedent database.',
      },
    ],
  },
  {
    id: 'RESEARCH_CASE_PREP',
    name: 'Case File Preparation',
    name_ar: 'إعداد ملف القضية',
    description:
      'Every Najiz filing must be digitally formatted and uploaded correctly. Preparation quality determines litigation efficiency.',
    category: 'research',
    persona_tags: ['junior_associate'],
    tools: ['/documents'],
    route: '/documents',
    icon: 'case-prep',
    steps: [
      {
        order: 1,
        name: 'File organization',
        name_ar: 'تنظيم الملف',
        detail:
          'Create structured digital file: correspondence, contracts, evidence, court filings, internal work product. OCR-searchable.',
      },
      {
        order: 2,
        name: 'Chronology & cast',
        name_ar: 'التسلسل الزمني والأطراف',
        detail:
          'Prepare detailed timeline with source references. Create cast of characters with roles and relationships.',
      },
      {
        order: 3,
        name: 'Submission preparation',
        name_ar: 'إعداد التقديمات',
        detail:
          'Draft/assist: Statement of Claim, memoranda, evidence schedules. Format per MOJ template for Najiz upload.',
      },
      {
        order: 4,
        name: 'Hearing logistics',
        name_ar: 'الترتيبات اللوجستية',
        detail:
          'Confirm hearing date on Najiz. Test video connection. Prepare hearing bundle. Attend and take detailed notes.',
      },
      {
        order: 5,
        name: 'Post-hearing follow-up',
        name_ar: 'المتابعة بعد الجلسة',
        detail:
          'Circulate hearing summary. Calendar deadlines. Begin responsive memorandum. Update case status tracker.',
      },
    ],
  },
  {
    id: 'RESEARCH_DUE_DILIGENCE',
    name: 'Due Diligence Execution',
    name_ar: 'تنفيذ العناية الواجبة',
    description:
      'Junior associates conduct bulk of DD. Quality directly impacts deal pricing, warranty negotiation, and post-completion risk.',
    category: 'research',
    persona_tags: ['junior_associate', 'corporate_lawyer'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'due-diligence',
    steps: [
      {
        order: 1,
        name: 'Checklist preparation',
        name_ar: 'إعداد قائمة التحقق',
        detail:
          'Customize DD checklist: corporate, regulatory, employment, real estate, contracts, litigation, IP, tax, environmental.',
      },
      {
        order: 2,
        name: 'Data room review',
        name_ar: 'مراجعة غرفة البيانات',
        detail:
          'Systematically review documents against checklist. Identify missing documents. Search MC, Najiz, SAIP, ZATCA portals.',
      },
      {
        order: 3,
        name: 'Issue identification',
        name_ar: 'تحديد المشكلات',
        detail:
          'Flag issues as Red/Amber/Green. KSA red flags: Saudization non-compliance, Waqf encumbrances, undisclosed RPTs.',
      },
      {
        order: 4,
        name: 'DD report drafting',
        name_ar: 'صياغة تقرير العناية الواجبة',
        detail:
          'Draft sections per workstream: overview, documents reviewed, findings, risk assessment, recommendations.',
      },
      {
        order: 5,
        name: 'Briefing & finalization',
        name_ar: 'العرض والتنهية',
        detail:
          'Compile unified report. Prepare executive summary. Present to deal team. Update as negotiations proceed.',
      },
    ],
  },
  {
    id: 'RESEARCH_REGULATORY_FILING',
    name: 'Regulatory Filing Support',
    name_ar: 'دعم الإيداعات التنظيمية',
    description:
      'Government portals (MC, MISA, ZATCA, GOSI, Qiwa, Muqeem) each have specific requirements and deadlines.',
    category: 'research',
    persona_tags: ['junior_associate'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'regulatory-filing',
    steps: [
      {
        order: 1,
        name: 'Filing requirements',
        name_ar: 'متطلبات الإيداع',
        detail:
          'Identify all filings: MC, MISA, ZATCA, GOSI, Qiwa, Muqeem, municipality. Create tracker with dependencies.',
      },
      {
        order: 2,
        name: 'Document assembly',
        name_ar: 'تجميع المستندات',
        detail:
          'Gather per portal specs: articles, IDs, CR, leases, resolutions, POAs, financials. Arabic versions required.',
      },
      {
        order: 3,
        name: 'Portal submission',
        name_ar: 'التقديم عبر البوابة',
        detail:
          'Log into portals. Complete Arabic forms. Upload documents. Pay fees. Save confirmation receipts.',
      },
      {
        order: 4,
        name: 'Follow-up & queries',
        name_ar: 'المتابعة والاستفسارات',
        detail:
          'Monitor status. Respond to government queries within deadlines. Escalate complex issues to partner.',
      },
      {
        order: 5,
        name: 'Post-approval documentation',
        name_ar: 'التوثيق بعد الموافقة',
        detail:
          'Download certificates. Update client file. Prepare compliance calendar of renewals and periodic filings.',
      },
    ],
  },
  {
    id: 'RESEARCH_CLIENT_COMMS',
    name: 'Client Communication & Support',
    name_ar: 'التواصل مع العملاء والدعم',
    description:
      'The junior associate is often the primary daily contact. Communication quality drives retention.',
    category: 'research',
    persona_tags: ['junior_associate'],
    tools: ['/conversations', '/documents'],
    route: '/conversations',
    icon: 'client-comms',
    steps: [
      {
        order: 1,
        name: 'Update preparation',
        name_ar: 'إعداد التحديثات',
        detail:
          'After each development: what happened, what it means, actions required, next steps, timeline. Bilingual.',
      },
      {
        order: 2,
        name: 'Meeting coordination',
        name_ar: 'تنسيق الاجتماعات',
        detail:
          'Schedule meetings. Prepare agendas, background briefs. Send calendar invitations.',
      },
      {
        order: 3,
        name: 'Document coordination',
        name_ar: 'تنسيق المستندات',
        detail:
          'Circulate execution versions. Arrange signing. Book MOJ notary appointments. Manage e-signatures.',
      },
      {
        order: 4,
        name: 'Time recording & billing',
        name_ar: 'تسجيل الوقت والفوترة',
        detail:
          'Record time daily. Prepare draft invoice narratives. Track budgets. Respond to billing queries.',
      },
      {
        order: 5,
        name: 'File maintenance & closure',
        name_ar: 'صيانة الملفات والإغلاق',
        detail:
          'Maintain files. At matter end: closing memo, archive, return originals, final invoice, client feedback.',
      },
    ],
  },

  // --------------------------------------------------------------------------
  // FIRM MANAGEMENT (Persona: Managing Partner)
  // --------------------------------------------------------------------------
  {
    id: 'MANAGEMENT_CLIENT_INTAKE',
    name: 'Client Intake & Engagement',
    name_ar: 'استقبال العملاء والتعاقد',
    description:
      'KSA AML requirements mandate strict KYC. Failed conflict checks expose the firm to sanctions and reputational ruin.',
    category: 'management',
    persona_tags: ['managing_partner'],
    tools: ['/documents'],
    route: '/documents',
    icon: 'client-intake',
    steps: [
      {
        order: 1,
        name: 'Inquiry triage',
        name_ar: 'فرز الاستفسارات',
        detail:
          'Log inquiry in CRM with source, matter type, urgency, value. Assign to relevant practice head.',
      },
      {
        order: 2,
        name: 'Conflict check',
        name_ar: 'فحص تعارض المصالح',
        detail:
          'Run party names (Arabic & English) against conflict database. Check sanctions lists (OFAC, UN, SAFIU).',
      },
      {
        order: 3,
        name: 'KYC / AML due diligence',
        name_ar: 'العناية الواجبة لمكافحة غسل الأموال',
        detail:
          'Collect CR, national ID/Iqama, UBO declarations. Verify via National Address and MC portal.',
      },
      {
        order: 4,
        name: 'Engagement letter',
        name_ar: 'خطاب التعاقد',
        detail:
          'Draft bilingual letter: scope, fees, payment terms, jurisdiction, PDPL obligations, termination. Arabic controls.',
      },
      {
        order: 5,
        name: 'Matter opening',
        name_ar: 'فتح الملف',
        detail:
          'Create in PMS with billing codes. Assign team. Set up document workspace. Calendar key dates.',
      },
    ],
  },
  {
    id: 'MANAGEMENT_BILLING',
    name: 'Financial Oversight & Billing',
    name_ar: 'الإشراف المالي والفوترة',
    description:
      'ZATCA VAT (15%) on legal services is mandatory. FATOORA e-invoicing Phase 2 compliance required.',
    category: 'management',
    persona_tags: ['managing_partner'],
    tools: ['/documents'],
    route: '/documents',
    icon: 'billing',
    steps: [
      {
        order: 1,
        name: 'Time & expense review',
        name_ar: 'مراجعة الوقت والمصروفات',
        detail:
          'Weekly review of timekeeper entries. Flag under-recording and over-budget matters.',
      },
      {
        order: 2,
        name: 'Invoice preparation',
        name_ar: 'إعداد الفواتير',
        detail:
          'Generate invoices per terms. Calculate VAT at 15%. Meet FATOORA Phase 2 requirements (XML, QR, stamp).',
      },
      {
        order: 3,
        name: 'Billing review',
        name_ar: 'مراجعة الفواتير',
        detail:
          'Review for write-offs, discounts, narrative clarity. For government: comply with Etimad platform requirements.',
      },
      {
        order: 4,
        name: 'Collections management',
        name_ar: 'إدارة التحصيل',
        detail:
          'Track 30/60/90-day aging. Escalate: reminder → partner call → formal demand → engagement suspension.',
      },
      {
        order: 5,
        name: 'Trust account management',
        name_ar: 'إدارة حساب الأمانة',
        detail:
          'Manage client trust accounts per SBA rules. Replenish retainers. Monthly reconciliation. Segregation from operating.',
      },
    ],
  },
  {
    id: 'MANAGEMENT_FIRM_COMPLIANCE',
    name: 'Firm Licensing & Compliance',
    name_ar: 'ترخيص المكتب والامتثال',
    description:
      'MOJ and SBA tightly regulate firm licensing, lawyer registration, and professional conduct.',
    category: 'management',
    persona_tags: ['managing_partner'],
    tools: ['/documents', '/research'],
    route: '/documents',
    icon: 'firm-compliance',
    steps: [
      {
        order: 1,
        name: 'License renewal',
        name_ar: 'تجديد الترخيص',
        detail:
          'File on Najiz before expiry. Submit partnership deed, lease, insurance. For foreign firms: dedicated Najiz service.',
      },
      {
        order: 2,
        name: 'Lawyer license management',
        name_ar: 'إدارة تراخيص المحامين',
        detail:
          'Track expiry dates. Ensure SBA CPD requirements met. Submit renewals on Najiz.',
      },
      {
        order: 3,
        name: 'SBA accreditation',
        name_ar: 'اعتماد هيئة المحامين',
        detail:
          'Monitor SASL compliance: qualification benchmarks, supervision ratios, specialization declarations.',
      },
      {
        order: 4,
        name: 'Ethics monitoring',
        name_ar: 'مراقبة الأخلاقيات',
        detail:
          'Maintain policies on conflicts, confidentiality, advertising restrictions. Respond to SBA disciplinary inquiries.',
      },
      {
        order: 5,
        name: 'AML program',
        name_ar: 'برنامج مكافحة غسل الأموال',
        detail:
          'Maintain firm AML policy. Annual risk assessment. Train all staff. Appoint Compliance Officer. Retain records 10 years.',
      },
    ],
  },
  {
    id: 'MANAGEMENT_BUSINESS_DEV',
    name: 'Business Development & Growth',
    name_ar: 'تطوير الأعمال والنمو',
    description:
      'Vision 2030 generates massive legal demand. Firms that fail to position strategically lose to international entrants.',
    category: 'management',
    persona_tags: ['managing_partner'],
    tools: ['/conversations', '/research'],
    route: '/conversations',
    icon: 'business-dev',
    steps: [
      {
        order: 1,
        name: 'Market opportunity mapping',
        name_ar: 'رصد فرص السوق',
        detail:
          'Analyze demand by sector: mega-projects, fintech, entertainment, sports, energy. Map against capabilities.',
      },
      {
        order: 2,
        name: 'Relationship cultivation',
        name_ar: 'تنمية العلاقات',
        detail:
          'Maintain relationship matrix. Schedule quarterly touchpoints. Attend FII, LEAP, SBA conferences.',
      },
      {
        order: 3,
        name: 'Pitch & proposals',
        name_ar: 'العروض والمقترحات',
        detail:
          'Respond to RFPs (government entities, PIF companies). Develop bilingual credentials. Include fee estimates.',
      },
      {
        order: 4,
        name: 'Thought leadership',
        name_ar: 'القيادة الفكرية',
        detail:
          'Publish on Saudi legal reforms. Contribute to Chambers/Legal 500. Host client seminars on regulatory changes.',
      },
      {
        order: 5,
        name: 'Strategic alliances',
        name_ar: 'التحالفات الاستراتيجية',
        detail:
          'Establish referral arrangements with international firms. Manage Big 4 referrals. Track attribution.',
      },
    ],
  },
  {
    id: 'MANAGEMENT_TALENT',
    name: 'Talent & People Management',
    name_ar: 'إدارة المواهب والموارد البشرية',
    description:
      'Acute talent shortage. Saudization applies to law firms. Retention directly impacts service quality.',
    category: 'management',
    persona_tags: ['managing_partner'],
    tools: ['/documents'],
    route: '/documents',
    icon: 'talent',
    steps: [
      {
        order: 1,
        name: 'Workforce planning',
        name_ar: 'تخطيط القوى العاملة',
        detail:
          'Calculate Nitaqat ratio. Plan hiring for Green/Platinum band. Budget for Saudi salary premiums.',
      },
      {
        order: 2,
        name: 'Recruitment & vetting',
        name_ar: 'التوظيف والتدقيق',
        detail:
          'Screen for MOJ license eligibility (Sharia/Law degree, 3-year experience). Verify SBA standing.',
      },
      {
        order: 3,
        name: 'Onboarding & training',
        name_ar: 'التأهيل والتدريب',
        detail:
          'Structured program: firm systems, billing, AML training, PDPL, ethics. Register training contracts with MOJ.',
      },
      {
        order: 4,
        name: 'Performance evaluation',
        name_ar: 'تقييم الأداء',
        detail:
          'Semi-annual reviews: billable hours, case outcomes, client feedback, BD contribution. Support SBA CPD.',
      },
      {
        order: 5,
        name: 'Retention & succession',
        name_ar: 'الاحتفاظ والتعاقب',
        detail:
          'Benchmark compensation. Offer equity/partnership tracks. Plan succession. Manage departures with handover.',
      },
    ],
  },
];

// ============================================================================
// Helper Functions
// ============================================================================

export function getWorkflowsByCategory(
  category: WorkflowCategory
): WorkflowDefinition[] {
  return WORKFLOW_REGISTRY.filter(w => w.category === category);
}

export function getWorkflowsByPersona(
  persona: PersonaTag
): WorkflowDefinition[] {
  return WORKFLOW_REGISTRY.filter(w => w.persona_tags.includes(persona));
}

export function getWorkflowById(id: string): WorkflowDefinition | undefined {
  return WORKFLOW_REGISTRY.find(w => w.id === id);
}

export function getCategoryMeta(
  category: WorkflowCategory
): WorkflowCategoryMeta | undefined {
  return WORKFLOW_CATEGORIES.find(c => c.id === category);
}

export function getGroupedWorkflows(): Record<
  WorkflowCategory,
  WorkflowDefinition[]
> {
  const groups = {} as Record<WorkflowCategory, WorkflowDefinition[]>;
  for (const cat of WORKFLOW_CATEGORIES) {
    groups[cat.id] = getWorkflowsByCategory(cat.id);
  }
  return groups;
}
