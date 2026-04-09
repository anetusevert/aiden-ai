'use client';

import { useEffect, useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion } from 'framer-motion';
import {
  WORKFLOW_CATEGORIES,
  getWorkflowsByCategory,
} from '@/lib/workflowRegistry';
import { reportScreenContext } from '@/lib/screenContext';
import {
  getWorkflowCategoryHref,
  renderCategoryIcon,
} from '@/lib/workflowPresentation';

const containerVariants = {
  hidden: {},
  visible: {
    transition: {
      staggerChildren: 0.06,
    },
  },
};

const cardVariants = {
  hidden: { opacity: 0, y: 20 },
  visible: {
    opacity: 1,
    y: 0,
    transition: {
      duration: 0.22,
      ease: 'easeOut',
    },
  },
};

export default function WorkflowHubPage() {
  const router = useRouter();
  const [pressedCard, setPressedCard] = useState<string | null>(null);

  const categories = useMemo(
    () =>
      WORKFLOW_CATEGORIES.map(category => ({
        ...category,
        count: getWorkflowsByCategory(category.id).length,
      })),
    []
  );

  useEffect(() => {
    reportScreenContext({
      route: '/workflows',
      page_title: 'Workflow Hub',
      document: null,
      ui_state: {
        page: 'workflow_hub',
        workflowId: null,
        category: null,
        currentStep: null,
        totalSteps: null,
        stepName: null,
        caseId: null,
      },
    });

    window.dispatchEvent(
      new CustomEvent('amin:context', {
        detail: {
          message:
            "You're in the Workflow Hub. Choose a category to begin - I'll guide you through each step.",
        },
      })
    );
  }, []);

  const handleNavigate = (category: string) => {
    setPressedCard(category);
    window.setTimeout(() => {
      router.push(getWorkflowCategoryHref(category as never));
      setPressedCard(null);
    }, 100);
  };

  return (
    <div className="workflow-hub-screen">
      <div className="workflow-page-intro">
        <span className="workflow-page-kicker">Workflow Hub</span>
        <h1 className="workflow-page-title">
          Choose the path Amin should guide.
        </h1>
        <p className="workflow-page-subtitle">
          Explore every workflow as a continuous journey, then drop straight
          into execution when you are ready.
        </p>
      </div>

      <motion.div
        className="workflow-hub-grid"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {categories.map(category => (
          <motion.button
            key={category.id}
            type="button"
            variants={cardVariants}
            whileTap={{ scale: 0.98, transition: { duration: 0.1 } }}
            animate={
              pressedCard === category.id ? { scale: 0.98 } : { scale: 1 }
            }
            className="workflow-hub-card-v2"
            onClick={() => handleNavigate(category.id)}
          >
            <div className="workflow-hub-card-head">
              <div className="workflow-hub-card-icon">
                {renderCategoryIcon(category.id, 22)}
              </div>
              <span className="workflow-hub-card-count">
                {category.count} workflows
              </span>
            </div>

            <div className="workflow-hub-card-copy">
              <h2>{category.name}</h2>
              <p>
                {category.name} workflows tailored for the GCC and KSA legal
                operating rhythm.
              </p>
            </div>

            <span className="workflow-hub-card-arrow" aria-hidden>
              &#8250;
            </span>
          </motion.button>
        ))}
      </motion.div>
    </div>
  );
}
