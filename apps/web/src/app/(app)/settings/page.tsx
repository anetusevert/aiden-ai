'use client';

import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import {
  apiClient,
  LLMConfigResponse,
  LLMConfigUpdate,
  LLMTestResult,
} from '@/lib/apiClient';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

type ProviderKey = 'openai' | 'anthropic' | 'openai_compatible' | 'stub';

interface ProviderOption {
  value: ProviderKey;
  label: string;
  description: string;
  needsApiKey: boolean;
  needsBaseUrl: boolean;
  models: { value: string; label: string }[];
  keyPlaceholder: string;
  keyHelpUrl?: string;
  keyHelpLabel?: string;
}

const PROVIDERS: ProviderOption[] = [
  {
    value: 'openai',
    label: 'OpenAI',
    description: 'GPT-4o, GPT-4 Turbo, o3 and more',
    needsApiKey: true,
    needsBaseUrl: false,
    models: [
      { value: 'gpt-4o', label: 'GPT-4o (Recommended)' },
      { value: 'gpt-4o-mini', label: 'GPT-4o Mini (Faster, cheaper)' },
      { value: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
      { value: 'o3-mini', label: 'o3-mini (Reasoning)' },
    ],
    keyPlaceholder: 'sk-...',
    keyHelpUrl: 'https://platform.openai.com/api-keys',
    keyHelpLabel: 'platform.openai.com/api-keys',
  },
  {
    value: 'anthropic',
    label: 'Anthropic',
    description: 'Claude Sonnet, Opus, Haiku',
    needsApiKey: true,
    needsBaseUrl: false,
    models: [
      {
        value: 'claude-sonnet-4-20250514',
        label: 'Claude Sonnet 4 (Recommended)',
      },
      {
        value: 'claude-opus-4-20250514',
        label: 'Claude Opus 4 (Most capable)',
      },
      { value: 'claude-3-5-haiku-20241022', label: 'Claude 3.5 Haiku (Fast)' },
    ],
    keyPlaceholder: 'sk-ant-...',
    keyHelpUrl: 'https://console.anthropic.com/settings/keys',
    keyHelpLabel: 'console.anthropic.com/settings/keys',
  },
  {
    value: 'openai_compatible',
    label: 'OpenAI-Compatible',
    description: 'Ollama, OpenRouter, vLLM, Together AI, Groq, LM Studio',
    needsApiKey: false,
    needsBaseUrl: true,
    models: [{ value: 'llama3', label: 'Llama 3 (default)' }],
    keyPlaceholder: 'API key (optional for local models)',
  },
  {
    value: 'stub',
    label: 'Stub (Test Mode)',
    description: 'No external API calls — returns placeholder responses',
    needsApiKey: false,
    needsBaseUrl: false,
    models: [],
    keyPlaceholder: '',
  },
];

function getProviderOption(key: string): ProviderOption {
  return PROVIDERS.find(p => p.value === key) || PROVIDERS[0];
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [config, setConfig] = useState<LLMConfigResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<LLMTestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [provider, setProvider] = useState<ProviderKey>('openai');
  const [model, setModel] = useState('gpt-4o');
  const [apiKey, setApiKey] = useState('');
  const [baseUrl, setBaseUrl] = useState('');
  const [customModel, setCustomModel] = useState('');

  const providerOption = getProviderOption(provider);
  const hasPresetModels = providerOption.models.length > 0;
  const isCustomModelMode =
    provider === 'openai_compatible' ||
    (hasPresetModels && model === '__custom__');

  const fetchConfig = useCallback(async () => {
    try {
      const data = await apiClient.getLLMConfig();
      setConfig(data);
      setProvider((data.provider || 'openai') as ProviderKey);
      const pOpt = getProviderOption(data.provider);
      const knownModel = pOpt.models.find(m => m.value === data.model);
      if (knownModel) {
        setModel(data.model || pOpt.models[0]?.value || '');
      } else if (data.model && pOpt.models.length > 0) {
        setModel('__custom__');
        setCustomModel(data.model);
      } else {
        setModel(data.model || pOpt.models[0]?.value || '');
        if (!knownModel && data.model) {
          setCustomModel(data.model);
        }
      }
      if (data.base_url) setBaseUrl(data.base_url);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleProviderChange = (newProvider: ProviderKey) => {
    setProvider(newProvider);
    setTestResult(null);
    setError(null);
    setSuccess(null);
    const pOpt = getProviderOption(newProvider);
    if (pOpt.models.length > 0) {
      setModel(pOpt.models[0].value);
    } else {
      setModel('');
    }
    setCustomModel('');
  };

  const getEffectiveModel = (): string | null => {
    if (provider === 'stub') return null;
    if (isCustomModelMode) return customModel || null;
    return model || null;
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    setTestResult(null);

    try {
      const body: LLMConfigUpdate = {
        provider,
        model: getEffectiveModel(),
      };
      if (apiKey) body.api_key = apiKey;
      if (providerOption.needsBaseUrl) body.base_url = baseUrl || null;

      const data = await apiClient.updateLLMConfig(body);
      setConfig(data);
      setApiKey('');
      setSuccess('LLM configuration saved successfully.');
      setTimeout(() => setSuccess(null), 4000);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to save');
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    setError(null);

    try {
      const data = await apiClient.testLLMConnection();
      setTestResult(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Test failed');
    } finally {
      setTesting(false);
    }
  };

  if (user?.role !== 'ADMIN') {
    return (
      <motion.div
        className="settings-page"
        variants={fadeUp}
        initial="hidden"
        animate="visible"
      >
        <div className="settings-card">
          <h1 className="settings-title">Settings</h1>
          <p className="settings-notice">
            Admin access required to manage settings.
          </p>
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      className="settings-page"
      variants={staggerContainer}
      initial="hidden"
      animate="visible"
    >
      <motion.div className="settings-header" variants={staggerItem}>
        <h1 className="settings-title">Settings</h1>
        <p className="settings-subtitle">
          Configure Amin&apos;s AI provider and API keys
        </p>
      </motion.div>

      <motion.div className="settings-card" variants={staggerItem}>
        <div className="settings-card-header">
          <div className="settings-card-icon">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="1.5"
            >
              <path d="M12 2a4 4 0 0 0-4 4v2H6a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V10a2 2 0 0 0-2-2h-2V6a4 4 0 0 0-4-4z" />
              <circle cx="12" cy="15" r="2" />
            </svg>
          </div>
          <div>
            <h2 className="settings-card-title">LLM Provider</h2>
            <p className="settings-card-desc">
              Connect an AI provider to enable Amin&apos;s full capabilities
            </p>
          </div>
        </div>

        {loading ? (
          <div className="settings-loading">
            <span className="spinner" />
          </div>
        ) : (
          <div className="settings-form">
            <div className="settings-status">
              <span
                className={`settings-status-dot ${config?.api_key_set || config?.provider === 'stub' || config?.provider === 'openai_compatible' ? 'active' : 'inactive'}`}
              />
              <span className="settings-status-text">
                {config?.api_key_set ||
                config?.provider === 'stub' ||
                config?.provider === 'openai_compatible'
                  ? `Connected — ${getProviderOption(config?.provider || 'stub').label} (${config?.model || 'default'})`
                  : 'Not configured — Amin is running in stub mode'}
              </span>
              {config?.api_key_preview && (
                <span className="settings-key-preview">
                  {config.api_key_preview}
                </span>
              )}
            </div>

            <div className="settings-field">
              <label className="settings-label" htmlFor="provider">
                Provider
              </label>
              <select
                id="provider"
                className="settings-select"
                value={provider}
                onChange={e =>
                  handleProviderChange(e.target.value as ProviderKey)
                }
              >
                {PROVIDERS.map(p => (
                  <option key={p.value} value={p.value}>
                    {p.label} — {p.description}
                  </option>
                ))}
              </select>
            </div>

            {provider !== 'stub' && (
              <>
                {hasPresetModels && (
                  <div className="settings-field">
                    <label className="settings-label" htmlFor="model">
                      Model
                    </label>
                    <select
                      id="model"
                      className="settings-select"
                      value={model}
                      onChange={e => setModel(e.target.value)}
                    >
                      {providerOption.models.map(m => (
                        <option key={m.value} value={m.value}>
                          {m.label}
                        </option>
                      ))}
                      <option value="__custom__">Custom model...</option>
                    </select>
                  </div>
                )}

                {isCustomModelMode && (
                  <div className="settings-field">
                    <label className="settings-label" htmlFor="customModel">
                      {hasPresetModels ? 'Custom Model Name' : 'Model Name'}
                    </label>
                    <input
                      id="customModel"
                      type="text"
                      className="settings-input"
                      placeholder="e.g. llama3, mixtral, gpt-4o..."
                      value={customModel}
                      onChange={e => setCustomModel(e.target.value)}
                    />
                  </div>
                )}

                {providerOption.needsBaseUrl && (
                  <div className="settings-field">
                    <label className="settings-label" htmlFor="baseUrl">
                      Base URL
                    </label>
                    <input
                      id="baseUrl"
                      type="url"
                      className="settings-input"
                      placeholder="http://localhost:11434/v1"
                      value={baseUrl}
                      onChange={e => setBaseUrl(e.target.value)}
                    />
                    <p className="settings-field-hint">
                      The OpenAI-compatible chat completions endpoint (must end
                      with /v1)
                    </p>
                  </div>
                )}

                {(providerOption.needsApiKey ||
                  provider === 'openai_compatible') && (
                  <div className="settings-field">
                    <label className="settings-label" htmlFor="apiKey">
                      API Key
                      {!providerOption.needsApiKey && (
                        <span className="settings-label-hint">
                          {' '}
                          — optional for local models
                        </span>
                      )}
                      {config?.api_key_set && (
                        <span className="settings-label-hint">
                          {' '}
                          — leave blank to keep current key
                        </span>
                      )}
                    </label>
                    <input
                      id="apiKey"
                      type="password"
                      className="settings-input"
                      placeholder={
                        config?.api_key_set
                          ? '••••••••••••'
                          : providerOption.keyPlaceholder
                      }
                      value={apiKey}
                      onChange={e => setApiKey(e.target.value)}
                      autoComplete="off"
                    />
                  </div>
                )}
              </>
            )}

            {error && (
              <div className="settings-alert settings-alert-error">{error}</div>
            )}
            {success && (
              <div className="settings-alert settings-alert-success">
                {success}
              </div>
            )}
            {testResult && (
              <div
                className={`settings-alert ${testResult.success ? 'settings-alert-success' : 'settings-alert-error'}`}
              >
                <strong>
                  {testResult.success ? 'Connection OK' : 'Connection Failed'}
                </strong>
                <br />
                {testResult.message}
              </div>
            )}

            <div className="settings-actions">
              <button
                className="settings-btn settings-btn-primary"
                onClick={handleSave}
                disabled={saving}
              >
                {saving ? 'Saving...' : 'Save Configuration'}
              </button>
              <button
                className="settings-btn settings-btn-secondary"
                onClick={handleTest}
                disabled={testing}
              >
                {testing ? 'Testing...' : 'Test Connection'}
              </button>
            </div>
          </div>
        )}
      </motion.div>

      {providerOption.keyHelpUrl && (
        <motion.div
          className="settings-card settings-card-info"
          variants={staggerItem}
        >
          <h3 className="settings-info-title">
            How to get a {providerOption.label} API key
          </h3>
          <ol className="settings-info-steps">
            <li>
              Go to{' '}
              <a
                href={providerOption.keyHelpUrl}
                target="_blank"
                rel="noopener noreferrer"
              >
                {providerOption.keyHelpLabel}
              </a>
            </li>
            <li>Create a new API key</li>
            <li>Copy the key and paste it above</li>
            <li>
              Click &quot;Save Configuration&quot;, then &quot;Test
              Connection&quot;
            </li>
          </ol>
          <p className="settings-info-note">
            Your API key is stored securely in the database and is never exposed
            in the UI after saving.
          </p>
        </motion.div>
      )}

      {provider === 'openai_compatible' && (
        <motion.div
          className="settings-card settings-card-info"
          variants={staggerItem}
        >
          <h3 className="settings-info-title">Using open-source models</h3>
          <p className="settings-info-note">
            Any service that exposes an OpenAI-compatible chat completions API
            will work. Common options:
          </p>
          <ul className="settings-info-steps">
            <li>
              <strong>Ollama</strong> — local, free. Base URL:{' '}
              <code>http://localhost:11434/v1</code>
            </li>
            <li>
              <strong>LM Studio</strong> — local, free. Base URL:{' '}
              <code>http://localhost:1234/v1</code>
            </li>
            <li>
              <strong>OpenRouter</strong> — cloud, many models. Base URL:{' '}
              <code>https://openrouter.ai/api/v1</code>
            </li>
            <li>
              <strong>Together AI</strong> — cloud, fast inference. Base URL:{' '}
              <code>https://api.together.xyz/v1</code>
            </li>
            <li>
              <strong>Groq</strong> — cloud, very fast. Base URL:{' '}
              <code>https://api.groq.com/openai/v1</code>
            </li>
          </ul>
        </motion.div>
      )}
    </motion.div>
  );
}
