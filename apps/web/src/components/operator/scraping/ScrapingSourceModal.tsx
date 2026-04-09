'use client';

import type { FormEvent } from 'react';
import { motion } from 'framer-motion';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Modal } from '@/components/ui/Modal';
import { Select } from '@/components/ui/Select';
import { glassReveal } from '@/lib/motion';
import { ScrapingSourceResponse } from '@/lib/apiClient';
import {
  CONNECTOR_OPTIONS,
  CUSTOM_SENTINEL,
  SCHEDULE_SELECT_OPTIONS,
} from './config';
import styles from './ScrapingControlCenter.module.css';

interface ScrapingSourceModalProps {
  mode: 'create' | 'edit';
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (event: FormEvent) => void;
  submitting: boolean;
  error: string | null;
  source?: ScrapingSourceResponse | null;
  connectorName: string;
  onConnectorNameChange: (value: string) => void;
  displayName: string;
  onDisplayNameChange: (value: string) => void;
  jurisdiction: string;
  onJurisdictionChange?: (value: string) => void;
  sourceUrl: string;
  onSourceUrlChange?: (value: string) => void;
  schedule: string;
  onScheduleChange: (value: string) => void;
  customCron: string;
  onCustomCronChange: (value: string) => void;
  harvestLimit: number;
  onHarvestLimitChange: (value: number) => void;
  enabled: boolean;
  onEnabledChange: (value: boolean) => void;
}

export function ScrapingSourceModal({
  mode,
  isOpen,
  onClose,
  onSubmit,
  submitting,
  error,
  source,
  connectorName,
  onConnectorNameChange,
  displayName,
  onDisplayNameChange,
  jurisdiction,
  onJurisdictionChange,
  sourceUrl,
  onSourceUrlChange,
  schedule,
  onScheduleChange,
  customCron,
  onCustomCronChange,
  harvestLimit,
  onHarvestLimitChange,
  enabled,
  onEnabledChange,
}: ScrapingSourceModalProps) {
  const isCreate = mode === 'create';
  const title = isCreate
    ? 'Add scraping source'
    : `Edit ${source?.display_name ?? 'source'}`;
  const formId = isCreate ? 'scraping-create-source' : 'scraping-edit-source';

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => {
        if (!submitting) onClose();
      }}
      title={title}
      size="lg"
      footer={
        <>
          <Button
            variant="outline"
            type="button"
            disabled={submitting}
            onClick={onClose}
          >
            Cancel
          </Button>
          <Button type="submit" form={formId} loading={submitting}>
            {isCreate ? 'Create source' : 'Save changes'}
          </Button>
        </>
      }
    >
      <motion.form
        id={formId}
        onSubmit={onSubmit}
        initial={glassReveal.initial}
        animate={glassReveal.animate}
        className={styles.sourceForm}
      >
        {error ? <p className="form-hint text-error">{error}</p> : null}

        {isCreate ? (
          <>
            <Select
              label="Connector"
              options={[...CONNECTOR_OPTIONS]}
              value={connectorName}
              onChange={e => onConnectorNameChange(e.target.value)}
            />
            <Input
              label="Jurisdiction"
              value={jurisdiction}
              onChange={e => onJurisdictionChange?.(e.target.value)}
              required
            />
            <Input
              label="Source URL"
              optional
              placeholder="https://..."
              value={sourceUrl}
              onChange={e => onSourceUrlChange?.(e.target.value)}
            />
          </>
        ) : (
          <div className={styles.readonlySourceMeta}>
            <div>
              <span className={styles.metaLabel}>Connector</span>
              <p>{source?.connector_name}</p>
            </div>
            <div>
              <span className={styles.metaLabel}>Jurisdiction</span>
              <p>{source?.jurisdiction}</p>
            </div>
          </div>
        )}

        <Input
          label="Display name"
          value={displayName}
          onChange={e => onDisplayNameChange(e.target.value)}
          required
        />

        <Select
          label="Schedule"
          options={SCHEDULE_SELECT_OPTIONS}
          value={schedule}
          onChange={e => onScheduleChange(e.target.value)}
        />

        {schedule === CUSTOM_SENTINEL ? (
          <Input
            label="Cron expression"
            hint="Five fields: minute hour day-of-month month day-of-week"
            value={customCron}
            onChange={e => onCustomCronChange(e.target.value)}
            placeholder="0 2 * * *"
          />
        ) : null}

        <Input
          label="Harvest limit"
          type="number"
          min={10}
          max={5000}
          value={harvestLimit}
          onChange={e =>
            onHarvestLimitChange(
              Math.min(5000, Math.max(10, parseInt(e.target.value, 10) || 10))
            )
          }
        />

        <label className={styles.toggleField}>
          <span>
            <span className={styles.toggleLabel}>Source enabled</span>
            <span className={styles.toggleHint}>
              Disabled sources stay visible but cannot be scheduled or
              triggered.
            </span>
          </span>
          <button
            type="button"
            role="switch"
            aria-checked={enabled}
            className={`${styles.switch} ${enabled ? styles.switchOn : ''}`}
            onClick={() => onEnabledChange(!enabled)}
          >
            <span className={styles.switchKnob} />
          </button>
        </label>
      </motion.form>
    </Modal>
  );
}
