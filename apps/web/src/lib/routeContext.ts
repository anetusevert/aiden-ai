import { getWorkflowById } from '@/lib/workflowRegistry';
import { getToolLabel } from '@/lib/workflowPresentation';

export interface RouteContext {
  label: string;
  headline: string;
  detail: string;
  icon: string;
}

const routeContextMap: Array<{ pattern: RegExp; context: RouteContext }> = [
  {
    pattern: /^\/documents\/[^/]+\/versions\/.+\/viewer$/,
    context: {
      label: 'Document Viewer',
      headline: 'Opening evidence viewer',
      detail:
        'Amin is preparing the cited passage and surrounding document context.',
      icon: 'M15 12a3 3 0 11-6 0 3 3 0 016 0z M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z',
    },
  },
  {
    pattern: /^\/documents\/[^/]+$/,
    context: {
      label: 'Document',
      headline: 'Loading document workspace',
      detail:
        'Amin is assembling document history, versions, and indexing status.',
      icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z',
    },
  },
  {
    pattern: /^\/home$/,
    context: {
      label: 'Home',
      headline: 'Returning to your command center',
      detail:
        'Amin is restoring your personalized launchpad and active workflow context.',
      icon: 'M3 10.5 12 3l9 7.5V21a1 1 0 0 1-1 1h-5v-7H9v7H4a1 1 0 0 1-1-1z',
    },
  },
  {
    pattern: /^\/news$/,
    context: {
      label: 'Legal Intelligence',
      headline: 'Refreshing legal intelligence',
      detail:
        'Amin is opening the visual news room and preparing the latest source-linked updates.',
      icon: 'M4 5h16v14H4zm3 3h10M7 12h10M7 16h6',
    },
  },
  {
    pattern: /^\/documents$/,
    context: {
      label: 'Documents',
      headline: 'Opening document vault',
      detail:
        'Amin is preparing your document inventory and recent indexing activity.',
      icon: 'M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z',
    },
  },
  {
    pattern: /^\/conversations$/,
    context: {
      label: 'Conversations',
      headline: 'Opening conversations',
      detail:
        'Amin is restoring your dialogue history and latest discussion threads.',
      icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z',
    },
  },
  {
    pattern: /^\/contract-review$/,
    context: {
      label: 'Contract Review',
      headline: 'Preparing contract review',
      detail:
        'Amin is opening the review workspace and aligning it with your selected legal workflow.',
      icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4',
    },
  },
  {
    pattern: /^\/clause-redlines$/,
    context: {
      label: 'Clause Analysis',
      headline: 'Preparing clause analysis',
      detail:
        'Amin is loading the clause workspace with the relevant workflow context.',
      icon: 'M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z',
    },
  },
  {
    pattern: /^\/research$/,
    context: {
      label: 'Research',
      headline: 'Preparing research workspace',
      detail:
        'Amin is connecting the right evidence sources and research filters.',
      icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z',
    },
  },
  {
    pattern: /^\/workflows\/[^/]+\/[^/]+$/,
    context: {
      label: 'Workflow',
      headline: 'Loading workflow guidance',
      detail:
        'Amin is preparing the workflow brief, steps, and recommended launch paths.',
      icon: 'M6 4h12M6 12h12M6 20h7',
    },
  },
  {
    pattern: /^\/workflows\/[^/]+$/,
    context: {
      label: 'Practice Area',
      headline: 'Loading practice area workflows',
      detail:
        'Amin is opening the category hub and organizing the relevant workflow options.',
      icon: 'M4 6h16M4 12h16M4 18h10',
    },
  },
  {
    pattern: /^\/global-legal\/[^/]+\/versions\/.+$/,
    context: {
      label: 'Legal Version',
      headline: 'Opening legal version',
      detail: 'Amin is preparing the selected legal text and version context.',
      icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
    },
  },
  {
    pattern: /^\/global-legal\/[^/]+$/,
    context: {
      label: 'Legal Instrument',
      headline: 'Opening legal instrument',
      detail:
        'Amin is loading the relevant statute, metadata, and official references.',
      icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
    },
  },
  {
    pattern: /^\/global-legal$/,
    context: {
      label: 'Legal Library',
      headline: 'Opening legal library',
      detail:
        'Amin is preparing the global legal corpus and your filtered instrument view.',
      icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253',
    },
  },
  {
    pattern: /^\/members\/[^/]+$/,
    context: {
      label: 'Member',
      headline: 'Opening member profile',
      detail: 'Amin is preparing workspace access context for this member.',
      icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
    },
  },
  {
    pattern: /^\/members$/,
    context: {
      label: 'Members',
      headline: 'Opening members and organizations',
      detail: 'Amin is preparing your workspace roster and access controls.',
      icon: 'M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z',
    },
  },
  {
    pattern: /^\/audit$/,
    context: {
      label: 'Audit Log',
      headline: 'Opening audit log',
      detail:
        'Amin is preparing audit trails, filters, and recent system activity.',
      icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2',
    },
  },
  {
    pattern: /^\/account\/amin$/,
    context: {
      label: 'Amin Settings',
      headline: 'Opening Amin settings',
      detail:
        'Amin is preparing your assistant preferences and communication profile.',
      icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
    },
  },
  {
    pattern: /^\/account\/twin$/,
    context: {
      label: 'Digital Twin',
      headline: 'Opening digital twin',
      detail: 'Amin is preparing your AI profile and learned work patterns.',
      icon: 'M5.121 17.804A13.937 13.937 0 0112 16c2.5 0 4.847.655 6.879 1.804M15 10a3 3 0 11-6 0 3 3 0 016 0zm6 2a9 9 0 11-18 0 9 9 0 0118 0z',
    },
  },
  {
    pattern: /^\/account$/,
    context: {
      label: 'Account',
      headline: 'Opening account settings',
      detail:
        'Amin is preparing your profile, permissions, and identity settings.',
      icon: 'M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z',
    },
  },
  {
    pattern: /^\/operator\//,
    context: {
      label: 'Operator',
      headline: 'Opening operator tools',
      detail: 'Amin is preparing the platform administration workspace.',
      icon: 'M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.066 2.573c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.573 1.066c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.066-2.573c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z M15 12a3 3 0 11-6 0 3 3 0 016 0z',
    },
  },
];

const fallbackContext: RouteContext = {
  label: 'Page',
  headline: 'Preparing workspace',
  detail: 'Amin is loading the next view and restoring your context.',
  icon: 'M13 10V3L4 14h7v7l9-11h-7z',
};

export function getRouteContext(pathname: string): RouteContext {
  const [routePath, queryString = ''] = pathname.split('?');
  const workflowId = new URLSearchParams(queryString).get('workflow');
  const workflow = getWorkflowById(workflowId || '');

  if (workflow) {
    return {
      label: workflow.name,
      headline: `Preparing ${workflow.name}`,
      detail: `Amin is launching ${getToolLabel(workflow.route)} as part of this workflow.`,
      icon: 'M4 6h16M4 12h16M4 18h10',
    };
  }

  for (const entry of routeContextMap) {
    if (entry.pattern.test(routePath)) {
      return entry.context;
    }
  }
  return fallbackContext;
}
