'use client';

import { useMemo, useEffect, useState, useCallback } from 'react';
import {
  WORKFLOW_REGISTRY,
  WORKFLOW_CATEGORIES,
  getGroupedWorkflows,
  type WorkflowDefinition,
  type WorkflowCategory,
  type WorkflowCategoryMeta,
} from '@/lib/workflowRegistry';
import {
  getTopWorkflows,
  getRecentWorkflows,
  trackWorkflowUsage,
} from '@/lib/workflowUsage';
import type { SoulDetail } from '@/lib/apiClient';

// ============================================================================
// Types
// ============================================================================

export interface ScoredWorkflow {
  workflow: WorkflowDefinition;
  score: number;
  reason: 'twin_match' | 'frequent' | 'recent' | 'default';
}

export interface ContinueWorkflow {
  workflow: WorkflowDefinition;
  lastAccessedAt: number;
}

export interface WorkflowGroup {
  category: WorkflowCategoryMeta;
  workflows: WorkflowDefinition[];
}

export interface SidebarWorkflowData {
  /** Top personalized workflows — driven by twin + usage signals */
  forYou: ScoredWorkflow[];
  /** Recently accessed workflows — quick resume */
  continueItems: ContinueWorkflow[];
  /** All workflows grouped by category */
  allGroups: WorkflowGroup[];
  /** Record a workflow access */
  trackAccess: (workflowId: string) => void;
  /** Re-compute scores (e.g. after soul update) */
  refresh: () => void;
}

// ============================================================================
// Scoring Algorithm
// ============================================================================

/**
 * Compute a twin-affinity score for a workflow based on soul dimensions.
 *
 * The algorithm matches workflow category and persona tags against the soul's
 * expertise dimensions. Higher dimension values and confidence produce higher
 * scores.
 */
function computeTwinScore(
  workflow: WorkflowDefinition,
  soul: SoulDetail | null
): number {
  if (!soul) return 0;

  let score = 0;

  const dims = soul.soul_dimensions || [];
  const expertiseDims = dims.filter(d => d.category === 'expertise');

  for (const dim of expertiseDims) {
    const labelLower = dim.label.toLowerCase();

    // Category match (e.g. soul dimension "litigation" matches workflow category "litigation")
    if (labelLower.includes(workflow.category)) {
      score += dim.value * dim.confidence * 0.6;
    }

    // Persona tag match (e.g. "corporate_lawyer" dimension matches persona tag)
    for (const tag of workflow.persona_tags) {
      const tagWords = tag.split('_');
      if (tagWords.some(w => labelLower.includes(w) && w.length > 3)) {
        score += dim.value * dim.confidence * 0.3;
      }
    }
  }

  // Work patterns boost
  const patterns = soul.work_patterns || {};
  const frequentActivities = (patterns as Record<string, unknown>)
    .frequent_activities;
  if (Array.isArray(frequentActivities)) {
    for (const activity of frequentActivities) {
      if (typeof activity === 'string') {
        const actLower = activity.toLowerCase();
        if (
          actLower.includes(workflow.category) ||
          workflow.name.toLowerCase().includes(actLower)
        ) {
          score += 0.15;
        }
      }
    }
  }

  return Math.min(score, 1);
}

/**
 * Merge twin scores with usage-based scores to produce a final ranked list.
 *
 * Weight distribution:
 * - Twin affinity: 40%
 * - Usage frequency: 35%
 * - Usage recency:  25%
 */
function rankWorkflows(soul: SoulDetail | null): ScoredWorkflow[] {
  const usageTop = getTopWorkflows(40);
  const usageMap = new Map(usageTop.map(u => [u.workflow_id, u.score]));

  const scored: ScoredWorkflow[] = WORKFLOW_REGISTRY.map(workflow => {
    const twinScore = computeTwinScore(workflow, soul);
    const usageScore = usageMap.get(workflow.id) || 0;

    const finalScore = twinScore * 0.4 + usageScore * 0.6;

    let reason: ScoredWorkflow['reason'] = 'default';
    if (twinScore > 0.2) reason = 'twin_match';
    else if (usageScore > 0.3) reason = 'frequent';
    else if (usageScore > 0) reason = 'recent';

    return { workflow, score: finalScore, reason };
  });

  scored.sort((a, b) => b.score - a.score);
  return scored;
}

// ============================================================================
// Hook
// ============================================================================

export function useSidebarWorkflows(
  soul: SoulDetail | null
): SidebarWorkflowData {
  const [refreshKey, setRefreshKey] = useState(0);

  const refresh = useCallback(() => {
    setRefreshKey(k => k + 1);
  }, []);

  const trackAccess = useCallback((workflowId: string) => {
    trackWorkflowUsage(workflowId);
    setRefreshKey(k => k + 1);
  }, []);

  // Recompute every time soul changes or refresh is triggered
  const forYou = useMemo(() => {
    void refreshKey; // dependency
    const ranked = rankWorkflows(soul);
    return ranked.filter(r => r.score > 0).slice(0, 7);
  }, [soul, refreshKey]);

  const continueItems = useMemo((): ContinueWorkflow[] => {
    void refreshKey;
    const recent = getRecentWorkflows();
    const now = Date.now();
    const threeDaysAgo = now - 3 * 24 * 60 * 60 * 1000;

    const items: ContinueWorkflow[] = [];
    for (const [wfId, ts] of Object.entries(recent)) {
      if (ts < threeDaysAgo) continue;
      const workflow = WORKFLOW_REGISTRY.find(w => w.id === wfId);
      if (workflow) {
        items.push({ workflow, lastAccessedAt: ts });
      }
    }

    items.sort((a, b) => b.lastAccessedAt - a.lastAccessedAt);
    return items.slice(0, 5);
  }, [refreshKey]);

  const allGroups = useMemo((): WorkflowGroup[] => {
    const grouped = getGroupedWorkflows();
    return WORKFLOW_CATEGORIES.map(cat => ({
      category: cat,
      workflows: grouped[cat.id] || [],
    })).filter(g => g.workflows.length > 0);
  }, []);

  return {
    forYou,
    continueItems,
    allGroups,
    trackAccess,
    refresh,
  };
}
