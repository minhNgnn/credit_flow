import React from 'react';

export interface BadgeProps {
  children?: React.ReactNode;
  /** @startingPoint section="Components" subtitle="Status pill — neutral, success, warning, danger, info, accent" viewport="700x120" */
  tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' | 'accent';
}
