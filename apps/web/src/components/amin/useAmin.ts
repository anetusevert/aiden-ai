'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { getApiBaseUrl } from '@/lib/api';
import { configureScreenContextTransport } from '@/lib/screenContext';

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface Conversation {
  id: string;
  title: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  toolCalls?: unknown;
  createdAt: string;
}

export interface ToolExecution {
  tool: string;
  params: Record<string, unknown>;
  status: 'running' | 'complete' | 'error' | 'pending_confirmation';
  summary?: string;
  riskLevel?: string;
}

export interface SubTaskInfo {
  description: string;
  status: 'running' | 'complete';
  summary?: string;
}

export type AminStatus =
  | 'idle'
  | 'listening'
  | 'thinking'
  | 'speaking'
  | 'error';

export interface AminState {
  conversations: Conversation[];
  activeConversation: Conversation | null;
  messages: Message[];
  isConnected: boolean;
  aminStatus: AminStatus;
  isStreaming: boolean;
  streamingContent: string;
  activeTools: ToolExecution[];
  subTasks: SubTaskInfo[];
}

// ---------------------------------------------------------------------------
// Hook
// ---------------------------------------------------------------------------

const MAX_RECONNECT_DELAY = 30_000;

export function useAmin() {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversation, setActiveConversationState] =
    useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isConnected, setIsConnected] = useState(false);
  const [aminStatus, setAminStatus] = useState<AminStatus>('idle');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [activeTools, setActiveTools] = useState<ToolExecution[]>([]);
  const [subTasks, setSubTasks] = useState<SubTaskInfo[]>([]);
  const [isPanelOpen, setIsPanelOpen] = useState(false);
  const [unreadCount, setUnreadCount] = useState(0);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptRef = useRef(0);
  const reconnectTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const streamingContentRef = useRef('');

  // ---- helpers ----

  const baseUrl = getApiBaseUrl();

  const apiFetch = useCallback(
    async <T>(path: string, init?: RequestInit): Promise<T> => {
      const res = await fetch(`${baseUrl}${path}`, {
        ...init,
        credentials: 'include',
        headers: {
          Accept: 'application/json',
          'Content-Type': 'application/json',
          ...(init?.headers as Record<string, string> | undefined),
        },
      });
      if (!res.ok) {
        const text = await res.text().catch(() => res.statusText);
        throw new Error(text);
      }
      return res.json() as Promise<T>;
    },
    [baseUrl]
  );

  // ---- WS helpers ----

  const getWsUrl = useCallback(
    (conversationId: string) => {
      const url = new URL(baseUrl, window.location.origin);
      url.protocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
      return `${url.origin}/ws/conversations/${conversationId}`;
    },
    [baseUrl]
  );

  const disconnectWs = useCallback(() => {
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setIsConnected(false);
  }, []);

  const connectWs = useCallback(
    (conversationId: string) => {
      disconnectWs();
      const ws = new WebSocket(getWsUrl(conversationId));
      wsRef.current = ws;

      ws.onopen = () => {
        setIsConnected(true);
        reconnectAttemptRef.current = 0;
        configureScreenContextTransport({
          connected: true,
          send: payload => ws.send(JSON.stringify(payload)),
        });
      };

      ws.onmessage = ev => {
        try {
          const data = JSON.parse(ev.data as string) as Record<string, unknown>;
          const type = data.type as string;

          switch (type) {
            case 'status':
              setAminStatus(data.status as AminStatus);
              break;

            case 'tool_start':
              setActiveTools(prev => [
                ...prev,
                {
                  tool: data.tool as string,
                  params: (data.params ?? {}) as Record<string, unknown>,
                  status: 'running',
                },
              ]);
              setAminStatus('thinking');
              break;

            case 'tool_result':
              setActiveTools(prev =>
                prev.map(t =>
                  t.tool === (data.tool as string) &&
                  (t.status === 'running' ||
                    t.status === 'pending_confirmation')
                    ? {
                        ...t,
                        status: (data.error
                          ? 'error'
                          : 'complete') as ToolExecution['status'],
                        summary: (data.summary ?? data.error ?? '') as string,
                      }
                    : t
                )
              );
              break;

            case 'confirmation_required':
              setActiveTools(prev => [
                ...prev.filter(
                  t =>
                    t.tool !== (data.tool as string) || t.status !== 'running'
                ),
                {
                  tool: data.tool as string,
                  params: (data.params ?? {}) as Record<string, unknown>,
                  status: 'pending_confirmation',
                  riskLevel: (data.risk_level ?? 'medium') as string,
                },
              ]);
              setAminStatus('listening');
              break;

            case 'token': {
              const tokenContent = data.content as string;
              setIsStreaming(true);
              setAminStatus('speaking');
              streamingContentRef.current += tokenContent;
              setStreamingContent(streamingContentRef.current);
              break;
            }

            case 'message_complete': {
              const finalContent = streamingContentRef.current;
              streamingContentRef.current = '';
              setMessages(prev => [
                ...prev,
                {
                  id: (data.message_id ?? crypto.randomUUID()) as string,
                  role: 'assistant' as const,
                  content: finalContent,
                  createdAt: new Date().toISOString(),
                },
              ]);
              setStreamingContent('');
              setIsStreaming(false);
              setActiveTools([]);
              setSubTasks([]);
              setAminStatus('idle');
              if (!isPanelOpen) setUnreadCount(c => c + 1);
              break;
            }

            case 'title_update': {
              const newTitle = data.title as string;
              setActiveConversationState(prev =>
                prev ? { ...prev, title: newTitle } : prev
              );
              setConversations(prev =>
                prev.map(c =>
                  c.id === activeConversation?.id
                    ? { ...c, title: newTitle }
                    : c
                )
              );
              break;
            }

            case 'heartbeat': {
              const heartbeatContent = data.content as string;
              setMessages(prev => [
                ...prev,
                {
                  id: crypto.randomUUID(),
                  role: 'assistant' as const,
                  content: heartbeatContent,
                  createdAt: new Date().toISOString(),
                },
              ]);
              if (!isPanelOpen) setUnreadCount(c => c + 1);
              break;
            }

            case 'collabora_reload':
              window.dispatchEvent(
                new CustomEvent('collabora-reload', {
                  detail: { docId: data.docId ?? data.doc_id },
                })
              );
              break;

            case 'collabora_navigate':
              window.dispatchEvent(
                new CustomEvent('collabora-navigate', {
                  detail: {
                    target_type: data.target_type,
                    target_value: data.target_value,
                  },
                })
              );
              break;

            case 'collabora_save':
              window.dispatchEvent(new CustomEvent('collabora-save'));
              break;

            case 'document_created':
              window.dispatchEvent(
                new CustomEvent('document_created', {
                  detail: { docId: data.docId ?? data.doc_id },
                })
              );
              break;

            case 'subtask_start': {
              const tasks = (data.tasks ?? []) as string[];
              setSubTasks(
                tasks.map(desc => ({ description: desc, status: 'running' }))
              );
              setAminStatus('thinking');
              break;
            }

            case 'subtask_complete': {
              const taskDesc = data.task as string;
              const taskSummary = data.summary as string;
              setSubTasks(prev =>
                prev.map(st =>
                  st.description === taskDesc
                    ? { ...st, status: 'complete', summary: taskSummary }
                    : st
                )
              );
              break;
            }

            case 'error':
              setAminStatus('error');
              setIsStreaming(false);
              break;
          }
        } catch {
          // ignore malformed frames
        }
      };

      ws.onclose = () => {
        setIsConnected(false);
        configureScreenContextTransport({ connected: false, send: null });
        const delay = Math.min(
          1000 * 2 ** reconnectAttemptRef.current,
          MAX_RECONNECT_DELAY
        );
        reconnectAttemptRef.current += 1;
        reconnectTimerRef.current = setTimeout(
          () => connectWs(conversationId),
          delay
        );
      };

      ws.onerror = () => {
        ws.close();
      };
    },
    [disconnectWs, getWsUrl, isPanelOpen, activeConversation]
  );

  // ---- public API ----

  const loadConversations = useCallback(async () => {
    try {
      const data = await apiFetch<{ conversations: Conversation[] }>(
        '/conversations?limit=20&offset=0&status=active'
      );
      setConversations(data.conversations);
    } catch {
      // silently ignore
    }
  }, [apiFetch]);

  const createConversation = useCallback(async () => {
    const conv = await apiFetch<Conversation>('/conversations', {
      method: 'POST',
    });
    setConversations(prev => [conv, ...prev]);
    setActiveConversationState(conv);
    setMessages([]);
    setActiveTools([]);
    setSubTasks([]);
    setStreamingContent('');
    connectWs(conv.id);
    return conv;
  }, [apiFetch, connectWs]);

  const setActiveConversation = useCallback(
    async (id: string) => {
      try {
        const data = await apiFetch<{
          id: string;
          title: string | null;
          status: string;
          created_at: string;
          updated_at?: string;
          messages: Array<{
            id: string;
            role: 'user' | 'assistant' | 'system' | 'tool';
            content: string;
            tool_calls?: unknown;
            created_at: string;
          }>;
        }>(`/conversations/${id}`);

        const conv: Conversation = {
          id: data.id,
          title: data.title,
          status: data.status,
          created_at: data.created_at,
          updated_at: data.updated_at ?? data.created_at,
        };

        setActiveConversationState(conv);
        setMessages(
          data.messages.map(m => ({
            id: m.id,
            role: m.role,
            content: m.content,
            toolCalls: m.tool_calls,
            createdAt: m.created_at,
          }))
        );
        setActiveTools([]);
        setSubTasks([]);
        setStreamingContent('');
        connectWs(id);
      } catch {
        // silently ignore
      }
    },
    [apiFetch, connectWs]
  );

  const sendMessage = useCallback(
    async (content: string) => {
      if (!activeConversation) return;

      const userMsg: Message = {
        id: crypto.randomUUID(),
        role: 'user',
        content,
        createdAt: new Date().toISOString(),
      };
      setMessages(prev => [...prev, userMsg]);
      setAminStatus('thinking');

      if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
        streamingContentRef.current = '';
        wsRef.current.send(JSON.stringify({ type: 'message', content }));
      } else {
        try {
          const data = await apiFetch<{
            message: {
              id: string;
              role: 'assistant';
              content: string;
              created_at: string;
            };
          }>(`/conversations/${activeConversation.id}/messages`, {
            method: 'POST',
            body: JSON.stringify({ content }),
          });

          setMessages(prev => [
            ...prev,
            {
              id: data.message.id,
              role: data.message.role,
              content: data.message.content,
              createdAt: data.message.created_at,
            },
          ]);
        } catch {
          setAminStatus('error');
        } finally {
          setAminStatus('idle');
        }
      }
    },
    [activeConversation, apiFetch]
  );

  const confirmTool = useCallback((toolName: string, approved: boolean) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({ type: 'confirm_tool', tool: toolName, approved })
      );
      setActiveTools(prev =>
        prev.map(t =>
          t.tool === toolName && t.status === 'pending_confirmation'
            ? {
                ...t,
                status: approved ? 'running' : 'error',
                summary: approved ? 'Approved' : 'Denied',
              }
            : t
        )
      );
      if (approved) {
        setAminStatus('thinking');
      }
    }
  }, []);

  const togglePanel = useCallback(() => {
    setIsPanelOpen(prev => {
      if (!prev) setUnreadCount(0);
      return !prev;
    });
  }, []);

  // clean up on unmount
  useEffect(() => {
    return () => {
      configureScreenContextTransport({ connected: false, send: null });
      disconnectWs();
    };
  }, [disconnectWs]);

  return {
    conversations,
    activeConversation,
    messages,
    isConnected,
    aminStatus,
    isStreaming,
    streamingContent,
    activeTools,
    subTasks,
    isPanelOpen,
    unreadCount,
    sendMessage,
    confirmTool,
    createConversation,
    loadConversations,
    setActiveConversation,
    togglePanel,
  };
}
