'use client';

import { motion } from 'framer-motion';

interface StepRailItem {
  title: string;
  estimate: string;
}

export function StepRail({
  steps,
  currentStep,
  completedSteps,
  onStepSelect,
  particleStep,
}: {
  steps: StepRailItem[];
  currentStep: number;
  completedSteps: number[];
  onStepSelect?: (stepIndex: number) => void;
  particleStep?: number | null;
}) {
  return (
    <aside className="workflow-step-rail">
      <div className="workflow-step-rail-head">
        <span className="workflow-page-kicker">Workflow Steps</span>
      </div>

      <div className="workflow-step-rail-list">
        {steps.map((step, index) => {
          const isComplete = completedSteps.includes(index);
          const isActive = index === currentStep;

          return (
            <div
              key={`${step.title}-${index}`}
              className="workflow-step-rail-item-shell"
            >
              {index > 0 ? (
                <motion.div
                  className="workflow-step-connector"
                  animate={{
                    backgroundColor: completedSteps.includes(index - 1)
                      ? 'rgba(255,255,255,0.75)'
                      : 'rgba(255,255,255,0.1)',
                  }}
                  transition={{ duration: 0.22, ease: 'easeOut' }}
                />
              ) : null}

              <button
                type="button"
                className="workflow-step-rail-item"
                data-state={
                  isComplete ? 'complete' : isActive ? 'active' : 'pending'
                }
                onClick={() => onStepSelect?.(index)}
              >
                <div className="workflow-step-rail-indicator-wrap">
                  {isActive ? (
                    <motion.span
                      layoutId="active-step-indicator"
                      className="workflow-step-rail-highlight"
                    />
                  ) : null}

                  <span className="workflow-step-rail-indicator">
                    {isComplete ? (
                      <svg
                        width="12"
                        height="12"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="2.5"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : (
                      <span>{index + 1}</span>
                    )}
                  </span>

                  {particleStep === index ? (
                    <div className="workflow-step-particles" aria-hidden>
                      {Array.from({ length: 6 }).map((_, particleIndex) => (
                        <motion.span
                          key={particleIndex}
                          className="workflow-step-particle"
                          initial={{ opacity: 1, scale: 1, x: 0, y: 0 }}
                          animate={{
                            opacity: 0,
                            scale: 2,
                            x: Math.cos((particleIndex / 6) * Math.PI * 2) * 20,
                            y: Math.sin((particleIndex / 6) * Math.PI * 2) * 20,
                          }}
                          transition={{ duration: 0.4, ease: 'easeOut' }}
                        />
                      ))}
                    </div>
                  ) : null}
                </div>

                <div className="workflow-step-rail-copy">
                  <span className="workflow-step-rail-title">{step.title}</span>
                  <span className="workflow-step-rail-estimate">
                    {step.estimate}
                  </span>
                </div>
              </button>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
