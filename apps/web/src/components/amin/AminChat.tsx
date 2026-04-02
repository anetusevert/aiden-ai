'use client';

import { useEffect, useRef } from 'react';
import { motion } from 'framer-motion';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { AminAvatarV2 } from './AminAvatarV2';
import type { AvatarState } from './AminAvatarV2';
import { AminToolStatus } from './AminToolStatus';
import { messageEnter, staggerContainer, staggerItem } from '@/lib/motion';
import type {
  Message,
  ToolExecution,
  SubTaskInfo,
  AminStatus,
} from './useAmin';

interface AminChatProps {
  messages: Message[];
  streamingContent: string;
  isStreaming: boolean;
  activeTools: ToolExecution[];
  subTasks: SubTaskInfo[];
  aminStatus: AminStatus;
  onSuggestion?: (text: string) => void;
  onConfirmTool?: (toolName: string, approved: boolean) => void;
}

const SUGGESTIONS = [
  'Review my latest contract',
  'Research UAE labor law updates',
  'Draft an NDA clause',
];

export function AminChat({
  messages,
  streamingContent,
  isStreaming,
  activeTools,
  subTasks,
  aminStatus,
  onSuggestion,
  onConfirmTool,
}: AminChatProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, activeTools, subTasks]);

  if (messages.length === 0 && !isStreaming) {
    return (
      <div className="amin-chat">
        <motion.div
          className="amin-empty"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, ease: [0.2, 0.8, 0.2, 1] }}
        >
          <AminAvatarV2
            size="full"
            state={aminStatus as AvatarState}
            showRing
          />
          <p className="amin-empty-greeting">
            {
              '\u0645\u0631\u062d\u0628\u0627\u064b \u064a\u0627 \u0645\u0633\u062a\u0634\u0627\u0631'
            }
          </p>
          <p className="amin-empty-subtitle">How can I help you today?</p>
          <motion.div
            className="amin-suggestions"
            variants={staggerContainer}
            initial="hidden"
            animate="visible"
          >
            {SUGGESTIONS.map(s => (
              <motion.button
                key={s}
                className="amin-suggestion-btn"
                onClick={() => onSuggestion?.(s)}
                variants={staggerItem}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
              >
                {s}
              </motion.button>
            ))}
          </motion.div>
        </motion.div>
      </div>
    );
  }

  return (
    <div className="amin-chat">
      {messages.map(msg => (
        <motion.div
          key={msg.id}
          className={`amin-message-row amin-message-row-${msg.role === 'user' ? 'user' : 'assistant'}`}
          variants={messageEnter}
          initial="hidden"
          animate="visible"
        >
          {msg.role !== 'user' && (
            <div className="amin-message-avatar">
              <AminAvatarV2 size="micro" state="idle" showRing={false} />
            </div>
          )}
          <div
            className={`amin-message amin-message-${msg.role === 'user' ? 'user' : 'assistant'}`}
          >
            {msg.role === 'user' ? (
              msg.content
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {msg.content}
              </ReactMarkdown>
            )}
          </div>
        </motion.div>
      ))}

      {(activeTools.length > 0 || subTasks.length > 0) && (
        <AminToolStatus
          tools={activeTools}
          subTasks={subTasks}
          onConfirm={onConfirmTool}
        />
      )}

      {isStreaming && streamingContent && (
        <motion.div
          className="amin-message-row amin-message-row-assistant"
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <div className="amin-message-avatar">
            <AminAvatarV2
              size="micro"
              state={aminStatus as AvatarState}
              showRing={false}
            />
          </div>
          <div className="amin-message amin-message-assistant">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {streamingContent}
            </ReactMarkdown>
            <span className="amin-streaming-cursor">{'\u258a'}</span>
          </div>
        </motion.div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
