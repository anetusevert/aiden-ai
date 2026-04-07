'use client';

import { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useAuth } from '@/lib/AuthContext';
import { getApiBaseUrl } from '@/lib/api';
import { fadeUp, staggerContainer, staggerItem } from '@/lib/motion';

interface LLMConfig {
  provider: string;
  model: string | null;
  api_key_set: boolean;
  api_key_preview: string | null;
}

interface TestResult {
  success: boolean;
  provider: string;
  model: string;
  message: string;
}

export default function SettingsPage() {
  const { user } = useAuth();
  const [config, setConfig] = useState<LLMConfig | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<TestResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [provider, setProvider] = useState('openai');
  const [model, setModel] = useState('gpt-4o');
  const [apiKey, setApiKey] = useState('');

  const baseUrl = getApiBaseUrl();

  const fetchConfig = useCallback(async () => {
    try {
      const res = await fetch(`${baseUrl}/admin/settings/llm`, {
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(await res.text());
      const data: LLMConfig = await res.json();
      setConfig(data);
      setProvider(data.provider);
      setModel(data.model || 'gpt-4o');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load settings');
    } finally {
      setLoading(false);
    }
  }, [baseUrl]);

  useEffect(() => {
    fetchConfig();
  }, [fetchConfig]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    setSuccess(null);
    setTestResult(null);

    try {
      const body: Record<string, string | null> = { provider, model };
      if (apiKey) body.api_key = apiKey;

      const res = await fetch(`${baseUrl}/admin/settings/llm`, {
        method: 'PUT',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          Accept: 'application/json',
        },
        body: JSON.stringify(body),
      });
      if (!res.ok) throw new Error(await res.text());
      const data: LLMConfig = await res.json();
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
      const res = await fetch(`${baseUrl}/admin/settings/llm/test`, {
        method: 'POST',
        credentials: 'include',
        headers: { Accept: 'application/json' },
      });
      if (!res.ok) throw new Error(await res.text());
      const data: TestResult = await res.json();
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
              Connect an OpenAI API key to enable Amin&apos;s full capabilities
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
                className={`settings-status-dot ${config?.api_key_set ? 'active' : 'inactive'}`}
              />
              <span className="settings-status-text">
                {config?.api_key_set
                  ? `Connected — ${config.provider} (${config.model || 'default'})`
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
                onChange={e => setProvider(e.target.value)}
              >
                <option value="openai">OpenAI</option>
                <option value="stub">Stub (Test Mode)</option>
              </select>
            </div>

            {provider === 'openai' && (
              <>
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
                    <option value="gpt-4o">GPT-4o (Recommended)</option>
                    <option value="gpt-4o-mini">
                      GPT-4o Mini (Faster, cheaper)
                    </option>
                    <option value="gpt-4-turbo">GPT-4 Turbo</option>
                    <option value="o3-mini">o3-mini (Reasoning)</option>
                  </select>
                </div>

                <div className="settings-field">
                  <label className="settings-label" htmlFor="apiKey">
                    API Key
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
                      config?.api_key_set ? '••••••••••••' : 'sk-...'
                    }
                    value={apiKey}
                    onChange={e => setApiKey(e.target.value)}
                    autoComplete="off"
                  />
                </div>
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
                {saving ? 'Saving…' : 'Save Configuration'}
              </button>
              <button
                className="settings-btn settings-btn-secondary"
                onClick={handleTest}
                disabled={testing || !config?.api_key_set}
              >
                {testing ? 'Testing…' : 'Test Connection'}
              </button>
            </div>
          </div>
        )}
      </motion.div>

      <motion.div
        className="settings-card settings-card-info"
        variants={staggerItem}
      >
        <h3 className="settings-info-title">How to get an API key</h3>
        <ol className="settings-info-steps">
          <li>
            Go to{' '}
            <a
              href="https://platform.openai.com/api-keys"
              target="_blank"
              rel="noopener noreferrer"
            >
              platform.openai.com/api-keys
            </a>
          </li>
          <li>Click &quot;Create new secret key&quot;</li>
          <li>Copy the key and paste it above</li>
          <li>
            Click &quot;Save Configuration&quot;, then &quot;Test
            Connection&quot;
          </li>
        </ol>
        <p className="settings-info-note">
          Your API key is stored securely in the database and is never exposed
          in the UI after saving. Amin uses GPT-4o by default for the best
          balance of capability and speed.
        </p>
      </motion.div>
    </motion.div>
  );
}
