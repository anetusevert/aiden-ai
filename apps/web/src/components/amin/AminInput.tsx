'use client';

import {
  useState,
  useCallback,
  useRef,
  useEffect,
  type KeyboardEvent,
  type ChangeEvent,
} from 'react';
import { useTranslations } from 'next-intl';

interface AminInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
  isStreaming?: boolean;
}

export function AminInput({
  onSend,
  disabled = false,
  isStreaming = false,
}: AminInputProps) {
  const t = useTranslations('amin');
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const isDisabled = disabled || isStreaming;
  const canSend = value.trim().length > 0 && !isDisabled;

  const autoResize = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 96)}px`;
  }, []);

  const handleSend = useCallback(() => {
    const trimmed = value.trim();
    if (!trimmed || isDisabled) return;
    // Reset sleep timer before sending
    window.dispatchEvent(new CustomEvent('amin-user-message'));
    onSend(trimmed);
    setValue('');
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  }, [value, isDisabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
    },
    [handleSend]
  );

  const handleChange = useCallback(
    (e: ChangeEvent<HTMLTextAreaElement>) => {
      setValue(e.target.value);
      autoResize();
    },
    [autoResize]
  );

  useEffect(() => {
    const handler = (event: Event) => {
      const customEvent = event as CustomEvent<{ text?: string }>;
      const nextValue = customEvent.detail?.text ?? '';
      setValue(nextValue);
      requestAnimationFrame(() => {
        textareaRef.current?.focus();
        autoResize();
      });
    };

    window.addEventListener('amin-prefill', handler as EventListener);
    return () => window.removeEventListener('amin-prefill', handler as EventListener);
  }, [autoResize]);

  return (
    <div className="amin-input-area">
      <div className="amin-input-container">
        <textarea
          ref={textareaRef}
          className="amin-input-textarea"
          value={value}
          onChange={handleChange}
          onKeyDown={handleKeyDown}
          placeholder={t('placeholderInput')}
          rows={1}
          disabled={isDisabled}
        />
        <button
          className="amin-input-send"
          onClick={handleSend}
          disabled={!canSend}
          aria-label={t('sendMessage')}
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="12" y1="19" x2="12" y2="5" />
            <polyline points="5,12 12,5 19,12" />
          </svg>
        </button>
      </div>
    </div>
  );
}
