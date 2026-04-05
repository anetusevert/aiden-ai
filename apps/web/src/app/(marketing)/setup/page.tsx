'use client';

import { useState, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  apiClient,
  BootstrapResponse,
  setStoredTenantId,
  setStoredWorkspaceId,
  setStoredWorkspaceContext,
} from '@/lib/apiClient';
import {
  WORKSPACE_TEMPLATES,
  getTemplateById,
  setStoredTemplateId,
  PrimaryJurisdiction,
  DataResidencyPolicy,
} from '@/lib/workspaceTemplates';

type WorkspaceType = 'IN_HOUSE' | 'LAW_FIRM';

type SetupStep =
  | 'idle'
  | 'creating_tenant'
  | 'signing_in'
  | 'creating_policy'
  | 'attaching_policy'
  | 'complete'
  | 'error';

const STEP_LABELS: Record<SetupStep, string> = {
  idle: 'Ready',
  creating_tenant: 'Creating tenant...',
  signing_in: 'Authenticating...',
  creating_policy: 'Configuring policy...',
  attaching_policy: 'Finalizing...',
  complete: 'Complete',
  error: 'Error',
};

const STEP_ORDER: SetupStep[] = [
  'creating_tenant',
  'signing_in',
  'creating_policy',
  'attaching_policy',
  'complete',
];

interface SetupStepperProps {
  currentStep: SetupStep;
}

function SetupStepper({ currentStep }: SetupStepperProps) {
  if (currentStep === 'idle') return null;

  const currentIndex = STEP_ORDER.indexOf(currentStep);

  return (
    <div className="setup-stepper">
      {STEP_ORDER.map((step, index) => {
        const isActive = step === currentStep;
        const isComplete = index < currentIndex || currentStep === 'complete';
        const isError = currentStep === 'error' && index === currentIndex;

        let circleClass = 'pending';
        if (isError) circleClass = 'error';
        else if (isComplete) circleClass = 'complete';
        else if (isActive) circleClass = 'active';

        const stepLabel =
          step === 'creating_tenant'
            ? 'Tenant'
            : step === 'signing_in'
              ? 'Auth'
              : step === 'creating_policy'
                ? 'Policy'
                : step === 'attaching_policy'
                  ? 'Finalize'
                  : 'Done';

        return (
          <div key={step} style={{ display: 'contents' }}>
            {index > 0 && (
              <div
                className={`setup-stepper-connector ${isComplete ? 'complete' : ''}`}
              />
            )}
            <div className={`setup-stepper-step ${isActive ? 'active' : ''}`}>
              <div className={`setup-stepper-circle ${circleClass}`}>
                {isComplete && !isError ? '✓' : isError ? '!' : index + 1}
              </div>
              <span className="setup-stepper-label">{stepLabel}</span>
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function SetupPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);
  const [currentStep, setCurrentStep] = useState<SetupStep>('idle');
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BootstrapResponse | null>(null);

  // Template selection
  const [selectedTemplateId, setSelectedTemplateId] = useState<string>(
    WORKSPACE_TEMPLATES[0].id
  );

  // Tenant fields
  const [tenantName, setTenantName] = useState('');
  const [primaryJurisdiction, setPrimaryJurisdiction] =
    useState<PrimaryJurisdiction>(
      WORKSPACE_TEMPLATES[0].recommendedJurisdiction
    );
  const [dataResidency, setDataResidency] = useState<DataResidencyPolicy>(
    WORKSPACE_TEMPLATES[0].recommendedDataResidency
  );

  const [residencyOverridden, setResidencyOverridden] = useState(false);

  // Bootstrap fields
  const [adminEmail, setAdminEmail] = useState('');
  const [adminPassword, setAdminPassword] = useState('');
  const [adminFullName, setAdminFullName] = useState('');
  const [workspaceName, setWorkspaceName] = useState('');
  const [workspaceType, setWorkspaceType] = useState<WorkspaceType>('IN_HOUSE');

  const selectedTemplate = getTemplateById(selectedTemplateId);

  // When template changes, update jurisdiction and residency to match
  useEffect(() => {
    if (selectedTemplate) {
      setPrimaryJurisdiction(selectedTemplate.recommendedJurisdiction);
      setDataResidency(selectedTemplate.recommendedDataResidency);
      setResidencyOverridden(false);
    }
  }, [selectedTemplate]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const u = await apiClient.getMe();
        if (!cancelled && !u.is_platform_admin) {
          router.replace('/');
        }
      } catch {
        /* not signed in — allowed for open dev bootstrap */
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [router]);

  const isResidencyMismatch =
    selectedTemplate &&
    dataResidency !== selectedTemplate.recommendedDataResidency;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    setCurrentStep('creating_tenant');

    const template = selectedTemplate;
    if (!template) {
      setError('Please select a workspace template');
      setLoading(false);
      setCurrentStep('error');
      return;
    }

    let bootstrapResponse: BootstrapResponse | null = null;
    let policyProfileId: string | null = null;

    try {
      // Step 1: Create tenant with bootstrap
      bootstrapResponse = await apiClient.bootstrapTenant({
        name: tenantName,
        primary_jurisdiction: primaryJurisdiction,
        data_residency_policy: dataResidency,
        bootstrap: {
          admin_user: {
            email: adminEmail,
            password: adminPassword,
            full_name: adminFullName || undefined,
          },
          workspace: {
            name: workspaceName,
            workspace_type: workspaceType,
            jurisdiction_profile:
              template.workspaceDefaults.jurisdiction_profile,
            default_language: template.workspaceDefaults.default_language,
          },
        },
      });

      if (bootstrapResponse.tenant_id) {
        setStoredTenantId(bootstrapResponse.tenant_id);
      }
      if (bootstrapResponse.workspace_id) {
        setStoredWorkspaceId(bootstrapResponse.workspace_id);
      }

      setCurrentStep('signing_in');

      // Step 2: Sign in (cookie session)
      await apiClient.login({
        email: adminEmail,
        password: adminPassword,
      });

      setCurrentStep('creating_policy');

      // Step 3: Create policy profile
      const policyResponse = await apiClient.createPolicyProfile({
        name: `${template.name} Policy`,
        description: template.description,
        config: template.policyConfig,
        is_default: true,
      });

      policyProfileId = policyResponse.id;

      setCurrentStep('attaching_policy');

      // Step 4: Attach policy profile to workspace
      await apiClient.attachWorkspacePolicyProfile(
        bootstrapResponse.workspace_id!,
        policyProfileId
      );

      setStoredTemplateId(template.id);

      setStoredWorkspaceContext({
        id: bootstrapResponse.workspace_id!,
        name: bootstrapResponse.workspace_name || workspaceName,
        default_language: template.workspaceDefaults.default_language,
        jurisdiction_profile: template.workspaceDefaults.jurisdiction_profile,
      });

      setCurrentStep('complete');
      setResult(bootstrapResponse);

      // Auto-redirect after delay
      setTimeout(() => {
        router.push('/home');
      }, 2500);
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Setup failed';
      setError(`${STEP_LABELS[currentStep]} failed: ${errorMessage}`);
      setCurrentStep('error');

      if (bootstrapResponse) {
        setResult(bootstrapResponse);
      }
    } finally {
      setLoading(false);
    }
  };

  // Success State
  if (result && currentStep === 'complete') {
    return (
      <div className="setup-container">
        <div className="setup-complete-card">
          <div className="setup-complete-header">
            <div className="setup-complete-icon">
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M20 6L9 17l-5-5" />
              </svg>
            </div>
            <h1 className="setup-complete-title">Setup Complete</h1>
            <p className="setup-complete-subtitle">
              Your workspace is ready. Redirecting to documents...
            </p>
          </div>

          <div className="setup-result-grid">
            <div className="setup-result-item">
              <span className="setup-result-label">Tenant</span>
              <span className="setup-result-value">{result.tenant_name}</span>
            </div>
            <div className="setup-result-item">
              <span className="setup-result-label">Tenant ID</span>
              <span className="setup-result-value mono">
                {result.tenant_id}
              </span>
            </div>
            {result.workspace_name && (
              <div className="setup-result-item">
                <span className="setup-result-label">Workspace</span>
                <span className="setup-result-value">
                  {result.workspace_name}
                </span>
              </div>
            )}
            {result.workspace_id && (
              <div className="setup-result-item">
                <span className="setup-result-label">Workspace ID</span>
                <span className="setup-result-value mono">
                  {result.workspace_id}
                </span>
              </div>
            )}
            {selectedTemplate && (
              <div className="setup-result-item">
                <span className="setup-result-label">Template</span>
                <span className="setup-result-value">
                  {selectedTemplate.name}
                </span>
              </div>
            )}
            {result.admin_user_email && (
              <div className="setup-result-item">
                <span className="setup-result-label">Administrator</span>
                <span className="setup-result-value">
                  {result.admin_user_email}
                </span>
              </div>
            )}
          </div>

          <div
            className="alert alert-neutral"
            style={{ marginBottom: 'var(--space-5)' }}
          >
            You have been signed in automatically. Your workspace is configured
            with the selected policy profile.
          </div>

          <button
            onClick={() => router.push('/home')}
            className="btn btn-primary btn-block"
          >
            Go to Home
          </button>
        </div>
      </div>
    );
  }

  // Form State
  return (
    <div className="setup-container">
      <div
        className="page-header"
        style={{ textAlign: 'center', marginBottom: 'var(--space-6)' }}
      >
        <h1 className="page-title">Workspace Setup</h1>
        <p className="page-subtitle">
          Configure your organization&apos;s workspace with jurisdiction and
          policy settings.
        </p>
      </div>

      <div className="setup-card">
        <SetupStepper currentStep={currentStep} />

        {error && <div className="alert alert-error">{error}</div>}

        <form onSubmit={handleSubmit}>
          {/* Section 1: Template Selection */}
          <div className="setup-section">
            <h3 className="setup-section-title">
              <span className="setup-section-number">1</span>
              Select Template
            </h3>

            <div className="form-group">
              <label htmlFor="template" className="form-label">
                Workspace Template
              </label>
              <select
                id="template"
                className="form-select"
                value={selectedTemplateId}
                onChange={e => setSelectedTemplateId(e.target.value)}
                required
                disabled={loading}
              >
                <optgroup label="UAE">
                  {WORKSPACE_TEMPLATES.filter(t => t.region === 'UAE').map(
                    template => (
                      <option key={template.id} value={template.id}>
                        {template.name}
                      </option>
                    )
                  )}
                </optgroup>
                <optgroup label="KSA">
                  {WORKSPACE_TEMPLATES.filter(t => t.region === 'KSA').map(
                    template => (
                      <option key={template.id} value={template.id}>
                        {template.name}
                      </option>
                    )
                  )}
                </optgroup>
              </select>
              {selectedTemplate && (
                <span className="form-hint">
                  {selectedTemplate.description}
                </span>
              )}
            </div>

            {selectedTemplate && (
              <div className="setup-template-preview">
                <div className="setup-template-row">
                  <span className="setup-template-label">Region</span>
                  <span className="badge badge-info">
                    {selectedTemplate.region}
                  </span>
                </div>
                <div className="setup-template-row">
                  <span className="setup-template-label">Workflows</span>
                  <span className="setup-template-value">
                    {selectedTemplate.policyConfig.allowed_workflows.join(', ')}
                  </span>
                </div>
                <div className="setup-template-row">
                  <span className="setup-template-label">Jurisdictions</span>
                  <span className="setup-template-value">
                    {selectedTemplate.policyConfig.allowed_jurisdictions.join(
                      ', '
                    )}
                  </span>
                </div>
                <div className="setup-template-row">
                  <span className="setup-template-label">Default Language</span>
                  <span className="setup-template-value">
                    {selectedTemplate.workspaceDefaults.default_language ===
                    'ar'
                      ? 'Arabic'
                      : selectedTemplate.workspaceDefaults.default_language ===
                          'en'
                        ? 'English'
                        : 'Mixed'}
                  </span>
                </div>
              </div>
            )}
          </div>

          {/* Section 2: Tenant Information */}
          <div className="setup-section">
            <h3 className="setup-section-title">
              <span className="setup-section-number">2</span>
              Tenant Information
            </h3>

            <div className="form-group">
              <label htmlFor="tenantName" className="form-label">
                Organization Name
              </label>
              <input
                id="tenantName"
                type="text"
                className="form-input"
                value={tenantName}
                onChange={e => setTenantName(e.target.value)}
                placeholder="e.g., Acme Legal Group"
                required
                disabled={loading}
              />
            </div>

            <div className="form-row form-row-2">
              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="jurisdiction" className="form-label">
                  Primary Jurisdiction
                </label>
                <select
                  id="jurisdiction"
                  className="form-select"
                  value={primaryJurisdiction}
                  onChange={e =>
                    setPrimaryJurisdiction(
                      e.target.value as PrimaryJurisdiction
                    )
                  }
                  disabled={loading}
                >
                  <option value="UAE">UAE</option>
                  <option value="DIFC">DIFC</option>
                  <option value="ADGM">ADGM</option>
                  <option value="KSA">KSA</option>
                </select>
              </div>

              <div className="form-group" style={{ marginBottom: 0 }}>
                <label htmlFor="residency" className="form-label">
                  Data Residency
                </label>
                <select
                  id="residency"
                  className="form-select"
                  value={dataResidency}
                  onChange={e => {
                    const newResidency = e.target.value as DataResidencyPolicy;
                    setDataResidency(newResidency);
                    setResidencyOverridden(
                      selectedTemplate
                        ? newResidency !==
                            selectedTemplate.recommendedDataResidency
                        : false
                    );
                  }}
                  disabled={loading}
                >
                  <option value="UAE">UAE</option>
                  <option value="KSA">KSA</option>
                  <option value="GCC">GCC</option>
                </select>
              </div>
            </div>

            {isResidencyMismatch && residencyOverridden && (
              <div
                className="alert alert-warning"
                style={{ marginTop: 'var(--space-4)' }}
              >
                Data residency ({dataResidency}) differs from template
                recommendation ({selectedTemplate?.recommendedDataResidency}).
              </div>
            )}
          </div>

          {/* Section 3: Administrator */}
          <div className="setup-section">
            <h3 className="setup-section-title">
              <span className="setup-section-number">3</span>
              Administrator Account
            </h3>

            <div className="form-group">
              <label htmlFor="adminEmail" className="form-label">
                Email Address
              </label>
              <input
                id="adminEmail"
                type="email"
                className="form-input"
                value={adminEmail}
                onChange={e => setAdminEmail(e.target.value)}
                placeholder="admin@organization.com"
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="adminPassword" className="form-label">
                Admin password
              </label>
              <input
                id="adminPassword"
                type="password"
                className="form-input"
                value={adminPassword}
                onChange={e => setAdminPassword(e.target.value)}
                placeholder="At least 8 characters"
                minLength={8}
                required
                disabled={loading}
                autoComplete="new-password"
              />
            </div>

            <div className="form-group">
              <label htmlFor="adminName" className="form-label">
                Full Name
                <span className="form-label-optional">(optional)</span>
              </label>
              <input
                id="adminName"
                type="text"
                className="form-input"
                value={adminFullName}
                onChange={e => setAdminFullName(e.target.value)}
                placeholder="Administrator name"
                disabled={loading}
              />
            </div>
          </div>

          {/* Section 4: Workspace */}
          <div className="setup-section">
            <h3 className="setup-section-title">
              <span className="setup-section-number">4</span>
              Workspace Details
            </h3>

            <div className="form-group">
              <label htmlFor="workspaceName" className="form-label">
                Workspace Name
              </label>
              <input
                id="workspaceName"
                type="text"
                className="form-input"
                value={workspaceName}
                onChange={e => setWorkspaceName(e.target.value)}
                placeholder="e.g., Main Workspace"
                required
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="workspaceType" className="form-label">
                Workspace Type
              </label>
              <select
                id="workspaceType"
                className="form-select"
                value={workspaceType}
                onChange={e =>
                  setWorkspaceType(e.target.value as WorkspaceType)
                }
                disabled={loading}
              >
                <option value="IN_HOUSE">In-House Legal</option>
                <option value="LAW_FIRM">Law Firm</option>
              </select>
            </div>
          </div>

          <button
            type="submit"
            className="btn btn-primary btn-block btn-lg"
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner spinner-sm" />
                {STEP_LABELS[currentStep]}
              </>
            ) : (
              'Create Workspace'
            )}
          </button>
        </form>

        <div className="auth-footer">
          <p>
            Already have a workspace? <Link href="/login">Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  );
}
