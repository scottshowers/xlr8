/**
 * StepIndicator.jsx - 7-Screen Flow Progress
 * ==========================================
 *
 * Shows the mockup's step indicator pills:
 * 1. Create Project
 * 2. Upload Data
 * 3. Auto-Analysis
 * 4. Findings
 * 5. Drill-In
 * 6. Build Playbook
 * 7. Track Progress
 *
 * Phase 4A UX Redesign - January 15, 2026
 */

import React from 'react';

const STEPS = [
  { num: 1, label: 'Create Project', path: '/projects/new' },
  { num: 2, label: 'Upload Data', path: '/upload' },
  { num: 3, label: 'Auto-Analysis', path: '/processing' },
  { num: 4, label: 'Findings', path: '/findings' },
  { num: 5, label: 'Drill-In', path: '/findings/' },
  { num: 6, label: 'Build Playbook', path: '/build-playbook' },
  { num: 7, label: 'Track Progress', path: '/progress' },
];

export default function StepIndicator({ currentStep = 1 }) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: 8,
      padding: '16px 24px',
      background: '#ffffff',
      borderBottom: '1px solid #e1e8ed',
    }}>
      {STEPS.map((step, index) => {
        const isActive = step.num === currentStep;
        const isCompleted = step.num < currentStep;

        return (
          <React.Fragment key={step.num}>
            {/* Step pill */}
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 8,
                padding: '8px 16px',
                borderRadius: 20,
                background: isActive ? '#83b16d' : isCompleted ? 'rgba(131, 177, 109, 0.15)' : '#f0f4f7',
                color: isActive ? '#ffffff' : isCompleted ? '#83b16d' : '#5f6c7b',
                fontSize: 13,
                fontWeight: 500,
                transition: 'all 0.2s',
                border: isActive ? 'none' : '1px solid #e1e8ed',
              }}
            >
              <span style={{
                width: 20,
                height: 20,
                borderRadius: '50%',
                background: isActive ? 'rgba(255,255,255,0.3)' : 'transparent',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                fontSize: 11,
                fontWeight: 700,
              }}>
                {step.num}
              </span>
              {step.label}
            </div>

            {/* Arrow between steps */}
            {index < STEPS.length - 1 && (
              <span style={{ color: '#c9d3d4', fontSize: 12 }}>→</span>
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
