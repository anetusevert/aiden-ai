'use client';

import { useSyncExternalStore } from 'react';

export interface ScreenDocumentContext {
  doc_id: string;
  title: string;
  doc_type: string;
  current_view: 'viewer' | 'editor';
  current_page: number | null;
  current_slide: number | null;
  current_sheet: string | null;
  metadata?: Record<string, unknown>;
}

export interface ScreenContextPayload {
  type?: 'screen_context';
  route: string;
  page_title: string;
  document: ScreenDocumentContext | null;
  ui_state: Record<string, unknown>;
}

type Listener = () => void;
type Sender = (payload: ScreenContextPayload) => void;

let currentPayload: ScreenContextPayload = {
  type: 'screen_context',
  route: '/',
  page_title: 'Workspace',
  document: null,
  ui_state: {},
};

interface ActiveCaseContext {
  case_id: string;
  case_title: string;
  client_name: string;
  practice_area?: string;
}

let activeCaseContext: ActiveCaseContext | null = null;

export function setActiveCaseContext(ctx: ActiveCaseContext | null) {
  activeCaseContext = ctx;
}

export function getActiveCaseContext() {
  return activeCaseContext;
}

let sender: Sender | null = null;
let connected = false;
const queue: ScreenContextPayload[] = [];
const listeners = new Set<Listener>();

function emit() {
  listeners.forEach(listener => listener());
}

export function subscribeScreenContext(listener: Listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getCurrentScreenContext() {
  return currentPayload;
}

export function useCurrentScreenContext() {
  return useSyncExternalStore(
    subscribeScreenContext,
    getCurrentScreenContext,
    getCurrentScreenContext
  );
}

export function configureScreenContextTransport(options: {
  connected: boolean;
  send: Sender | null;
}) {
  connected = options.connected;
  sender = options.send;
  if (connected && sender && queue.length > 0) {
    while (queue.length > 0) {
      const next = queue.shift();
      if (next) sender({ ...next, type: 'screen_context' });
    }
  }
}

export function reportScreenContext(payload: ScreenContextPayload) {
  const enrichedState = { ...payload.ui_state };
  if (activeCaseContext) {
    enrichedState.active_case_id = activeCaseContext.case_id;
    enrichedState.active_case_title = activeCaseContext.case_title;
    enrichedState.active_case_client = activeCaseContext.client_name;
    if (activeCaseContext.practice_area)
      enrichedState.active_case_practice_area = activeCaseContext.practice_area;
  }
  currentPayload = {
    ...payload,
    ui_state: enrichedState,
    type: 'screen_context',
  };
  emit();

  if (connected && sender) {
    sender(currentPayload);
    return;
  }

  queue.length = 0;
  queue.push(currentPayload);
}
