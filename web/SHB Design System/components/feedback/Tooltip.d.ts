import React from 'react';

export interface TooltipProps {
  children?: React.ReactNode;
  /** @startingPoint section="Components" subtitle="Hover label, navy-inverse background" viewport="700x120" */
  label?: string;
  side?: 'top' | 'bottom';
}
