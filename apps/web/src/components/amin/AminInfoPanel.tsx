'use client';

import { useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslations } from 'next-intl';
import { useAminContext } from './AminProvider';
import { AminAvatar, type AminAvatarState } from './AminAvatar';
import { AminInput } from './AminInput';
import { AminToolStatus } from './AminToolStatus';
import {
  MessageCard,
  UserQueryCard,
  StatusCard,
  StreamingCard,
  ActionCard,
} from './InfoCards';
import { useCurrentScreenContext } from '@/lib/screenContext';

const panelVariants = {
  collapsed: {
    opacity: 0,
    scale: 0.92,
    y: 40,
    transition: { duration: 0.25, ease: [0.4, 0, 0.2, 1] },
  },
  expanded: {
    opacity: 1,
    scale: 1,
    y: 0,
    transition: { duration: 0.35, ease: [0.2, 0.8, 0.2, 1] },
  },
};

const backdropVariants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.25 } },
  exit: { opacity: 0, transition: { duration: 0.2 } },
};

export function AminInfoPanel() {
  const t = useTranslations('amin');
  const {
    messages,
    aminStatus,
    isStreaming,
    streamingContent,
    activeTools,
    subTasks,
    activeConversation,
    sendMessage,
    confirmTool,
    createConversation,
    closePanel,
    panelSize,
    setPanelSize,
  } = useAminContext();

  const screenContext = useCurrentScreenContext();
  const documentContext = screenContext.document;
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!activeConversation) {
      createConversation().catch(() => {});
    }
  }, [activeConversation, createConversation]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, activeTools, subTasks]);

  const statusLabel =
    aminStatus === 'thinking'
      ? t('statusThinking')
      : aminStatus === 'speaking'
        ? t('statusSpeaking')
        : aminStatus === 'listening'
          ? t('statusListening')
          : aminStatus === 'error'
            ? t('statusError')
            : t('statusOnline');

  const handleDocumentShortcut = () => {
    if (!documentContext) return;
    window.dispatchEvent(
      new CustomEvent('amin-prefill', {
        detail: {
          text: `Please help me improve this document: ${documentContext.title}`,
        },
      })
    );
  };

  const toggleFullscreen = () => {
    setPanelSize(panelSize === 'fullscreen' ? 'expanded' : 'fullscreen');
  };

  const panelCls = `amin-info-panel amin-info-panel-${panelSize}`;

  return (
    <>
      {/* Backdrop / dimming layer */}
      <motion.div
        className="amin-info-backdrop"
        variants={backdropVariants}
        initial="hidden"
        animate="visible"
        exit="exit"
        onClick={closePanel}
      />

      {/* Panel */}
      <motion.div
        className={panelCls}
        variants={panelVariants}
        initial="collapsed"
        animate="expanded"
        exit="collapsed"
      >
        {/* ─── Header ──────────────────────────────────────── */}
        <div className="amin-info-header">
          <div className="amin-info-header-left">
            <AminAvatar
              size={48}
              state={aminStatus as AminAvatarState}
              showWaveform={false}
            />
            <div className="amin-info-header-meta">
              <span className="amin-info-title">{t('title')}</span>
              <span className="amin-info-status">
                <span className="amin-info-dot" data-status={aminStatus} />
                {statusLabel}
              </span>
            </div>
          </div>
          <div className="amin-info-header-actions">
            <button
              className="amin-info-btn"
              onClick={toggleFullscreen}
              aria-label={panelSize === 'fullscreen' ? 'Shrink' : 'Expand'}
              type="button"
            >
              {panelSize === 'fullscreen' ? <ShrinkIcon /> : <ExpandIcon />}
            </button>
            <button
              className="amin-info-btn"
              onClick={closePanel}
              aria-label={t('closePanel')}
              type="button"
            >
              <CloseIcon />
            </button>
          </div>
        </div>

        {/* ─── Document context banner ─────────────────────── */}
        {documentContext && (
          <div className="amin-info-context">
            <div>
              <div className="amin-info-context-title">
                {documentContext.title}
              </div>
              <div className="amin-info-context-badge">
                {documentContext.doc_type.toUpperCase()} ·{' '}
                {documentContext.current_view.toUpperCase()}
              </div>
            </div>
            <button
              className="btn btn-outline btn-sm"
              onClick={handleDocumentShortcut}
            >
              Edit with Amin
            </button>
          </div>
        )}

        {/* ─── Cards area ──────────────────────────────────── */}
        <div className="amin-info-cards">
          {messages.length === 0 && !isStreaming ? (
            <motion.div
              className="amin-info-empty"
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.15, duration: 0.4 }}
            >
              <AminAvatar
                size={72}
                state={aminStatus as AminAvatarState}
                showWaveform={false}
              />
              <p className="amin-info-greeting">{t('greetingSubtitleEn')}</p>
              <p className="amin-info-subtitle">{t('greetingSubtitle')}</p>
            </motion.div>
          ) : (
            <AnimatePresence mode="popLayout">
              {messages.map(msg =>
                msg.role === 'user' ? (
                  <UserQueryCard key={msg.id} content={msg.content} />
                ) : (
                  <MessageCard key={msg.id} content={msg.content} />
                )
              )}
            </AnimatePresence>
          )}

          {/* Active tool cards */}
          <AnimatePresence>
            {activeTools.map(tool =>
              tool.status === 'pending_confirmation' ? (
                <ActionCard
                  key={`action-${tool.tool}`}
                  title={`Confirm: ${tool.tool.replace(/_/g, ' ')}`}
                  description={`Amin wants to execute ${tool.tool}. Risk level: ${tool.riskLevel ?? 'medium'}`}
                  riskLevel={tool.riskLevel}
                  onConfirm={() => confirmTool(tool.tool, true)}
                  onDeny={() => confirmTool(tool.tool, false)}
                />
              ) : (
                <StatusCard
                  key={`status-${tool.tool}`}
                  tool={tool.tool}
                  status={tool.status}
                  summary={tool.summary}
                />
              )
            )}
          </AnimatePresence>

          {/* Sub-tasks (legacy tool status) */}
          {(activeTools.length > 0 || subTasks.length > 0) && (
            <AminToolStatus
              tools={activeTools}
              subTasks={subTasks}
              onConfirm={confirmTool}
            />
          )}

          {/* Streaming card */}
          <AnimatePresence>
            {isStreaming && streamingContent && (
              <StreamingCard key="streaming" content={streamingContent} />
            )}
          </AnimatePresence>

          <div ref={bottomRef} />
        </div>

        {/* ─── Input ───────────────────────────────────────── */}
        <AminInput
          onSend={sendMessage}
          isStreaming={isStreaming}
          disabled={!activeConversation}
        />
      </motion.div>
    </>
  );
}

/* ─── Icon helpers ─────────────────────────────────────────────────── */

function ExpandIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <polyline points="15 3 21 3 21 9" />
      <polyline points="9 21 3 21 3 15" />
      <line x1="21" y1="3" x2="14" y2="10" />
      <line x1="3" y1="21" x2="10" y2="14" />
    </svg>
  );
}

function ShrinkIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
    >
      <polyline points="4 14 10 14 10 20" />
      <polyline points="20 10 14 10 14 4" />
      <line x1="14" y1="10" x2="21" y2="3" />
      <line x1="3" y1="21" x2="10" y2="14" />
    </svg>
  );
}

function CloseIcon() {
  return (
    <svg
      width="16"
      height="16"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
    >
      <line x1="18" y1="6" x2="6" y2="18" />
      <line x1="6" y1="6" x2="18" y2="18" />
    </svg>
  );
}
