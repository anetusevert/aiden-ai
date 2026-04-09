'use client';

export type ContextPaneMode = 'top_bar' | 'left_panel' | 'hidden';

export type ContextPaneCardType =
  | 'client_card'
  | 'case_card'
  | 'research_card'
  | 'risk_card'
  | 'timeline_card'
  | 'comparison_card'
  | 'document_card'
  | 'regulatory_card'
  | 'priority_matrix'
  | 'text_card'
  | 'action_card';

export interface ContextPaneCardAction {
  label: string;
  event: string;
  params?: Record<string, unknown>;
}

export interface ContextPaneCardData {
  id: string;
  type: ContextPaneCardType;
  title: string;
  subtitle?: string;
  data: Record<string, unknown>;
  actions?: ContextPaneCardAction[];
  timestamp: number;
}

export interface ContextPanePushEventDetail {
  card: ContextPaneCardData;
  mode?: Exclude<ContextPaneMode, 'hidden'>;
}
