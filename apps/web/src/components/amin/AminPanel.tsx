'use client';

import { useEffect } from 'react';
import { motion } from 'framer-motion';
import { AminAvatarV2 } from './AminAvatarV2';
import type { AvatarState } from './AminAvatarV2';
import { AminChat } from './AminChat';
import { AminInput } from './AminInput';
import { useAminContext } from './AminProvider';
import { motionTokens } from '@/lib/motion';

const leftPanelMotion = {
  initial: { x: '-100%', opacity: 0.6 },
  animate: { x: 0, opacity: 1, transition: motionTokens.spring },
  exit: {
    x: '-100%',
    opacity: 0.5,
    transition: {
      duration: motionTokens.duration.fast,
      ease: motionTokens.ease,
    },
  },
};

export function AminPanel() {
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
  } = useAminContext();

  useEffect(() => {
    if (!activeConversation) {
      createConversation().catch(() => {});
    }
  }, [activeConversation, createConversation]);

  const statusLabel =
    aminStatus === 'thinking'
      ? 'Thinking\u2026'
      : aminStatus === 'speaking'
        ? 'Responding\u2026'
        : aminStatus === 'listening'
          ? 'Awaiting approval\u2026'
          : aminStatus === 'error'
            ? 'Error'
            : 'Online';

  const handleSuggestion = (text: string) => {
    sendMessage(text);
  };

  return (
    <motion.div
      className="amin-panel"
      key="amin-panel"
      initial={leftPanelMotion.initial}
      animate={leftPanelMotion.animate}
      exit={leftPanelMotion.exit}
    >
      {/* Header */}
      <div className="amin-panel-header">
        <AminAvatarV2
          size="small"
          state={aminStatus as AvatarState}
          showRing={false}
        />
        <div className="amin-panel-header-info">
          <span className="amin-panel-title">Amin</span>
          <span className="amin-panel-status">
            <span className="amin-panel-status-dot" data-status={aminStatus} />
            {statusLabel}
          </span>
        </div>
        <button
          className="amin-panel-close"
          onClick={closePanel}
          aria-label="Close Amin panel"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>

      {/* Chat Area */}
      <AminChat
        messages={messages}
        streamingContent={streamingContent}
        isStreaming={isStreaming}
        activeTools={activeTools}
        subTasks={subTasks}
        aminStatus={aminStatus}
        onSuggestion={handleSuggestion}
        onConfirmTool={confirmTool}
      />

      {/* Input */}
      <AminInput
        onSend={sendMessage}
        isStreaming={isStreaming}
        disabled={!activeConversation}
      />
    </motion.div>
  );
}
