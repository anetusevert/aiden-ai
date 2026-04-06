'use client';

import { useNav } from '@/context/NavigationContext';
import { HomePanel } from './panels/HomePanel';
import { ClientsPanel } from './panels/ClientsPanel';
import { CasesPanel } from './panels/CasesPanel';
import { WorkflowsPanel } from './panels/WorkflowsPanel';
import { DocumentsPanel } from './panels/DocumentsPanel';
import { IntelligencePanel } from './panels/IntelligencePanel';
import { AdminPanel } from './panels/AdminPanel';
import type { SoulDetail } from '@/lib/apiClient';

interface Rail2PanelProps {
  soul: SoulDetail | null;
}

export function Rail2Panel({ soul }: Rail2PanelProps) {
  const { activeSection, panelOpen, collapsePanel } = useNav();

  return (
    <div className={`rail2${panelOpen ? ' rail2-open' : ''}`}>
      <div className="rail2-inner">
        <button
          className="rail2-collapse"
          onClick={collapsePanel}
          type="button"
          aria-label="Collapse panel"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <polyline points="11,17 6,12 11,7" />
            <polyline points="18,17 13,12 18,7" />
          </svg>
        </button>

        <div className="rail2-content">
          {activeSection === 'home' && <HomePanel soul={soul} />}
          {activeSection === 'clients' && <ClientsPanel />}
          {activeSection === 'cases' && <CasesPanel />}
          {activeSection === 'workflows' && <WorkflowsPanel />}
          {activeSection === 'documents' && <DocumentsPanel />}
          {activeSection === 'intelligence' && <IntelligencePanel />}
          {activeSection === 'admin' && <AdminPanel />}
        </div>
      </div>
    </div>
  );
}
