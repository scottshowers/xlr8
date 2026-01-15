import React from 'react';
import { useNavigate } from 'react-router-dom';
import './FlowBar.css';

/**
 * FlowBar Component
 * 
 * Contextual 7-step progress indicator
 * Only shows when inside a project workflow
 * Steps: Create → Upload → Analysis → Findings → Detail → Playbook → Progress
 */

export const FlowBar = ({ currentStep = 1, projectId, steps = [] }) => {
  const navigate = useNavigate();

  // Default 7-step flow if not provided
  const defaultSteps = [
    { num: 1, label: 'Create', path: '/projects/new' },
    { num: 2, label: 'Upload', path: `/projects/${projectId}/upload` },
    { num: 3, label: 'Analysis', path: `/projects/${projectId}/processing` },
    { num: 4, label: 'Findings', path: `/projects/${projectId}/findings` },
    { num: 5, label: 'Detail', path: `/projects/${projectId}/findings/:id` },
    { num: 6, label: 'Playbook', path: `/projects/${projectId}/playbooks` },
    { num: 7, label: 'Progress', path: `/projects/${projectId}/progress` },
  ];

  const flowSteps = steps.length > 0 ? steps : defaultSteps;

  const getStepClass = (stepNum) => {
    if (stepNum < currentStep) return 'xlr8-flow-step--completed';
    if (stepNum === currentStep) return 'xlr8-flow-step--active';
    return '';
  };

  const handleStepClick = (step) => {
    // Only allow clicking on completed or current steps
    if (step.num <= currentStep && step.path && projectId) {
      navigate(step.path);
    }
  };

  return (
    <div className="xlr8-flow-bar">
      {flowSteps.map((step, index) => (
        <React.Fragment key={step.num}>
          <div 
            className={`xlr8-flow-step ${getStepClass(step.num)}`}
            onClick={() => handleStepClick(step)}
          >
            <span className="xlr8-flow-step__num">{step.num}</span>
            <span className="xlr8-flow-step__label">{step.label}</span>
          </div>
          
          {index < flowSteps.length - 1 && (
            <span className="xlr8-flow-arrow">→</span>
          )}
        </React.Fragment>
      ))}
    </div>
  );
};

export default FlowBar;
