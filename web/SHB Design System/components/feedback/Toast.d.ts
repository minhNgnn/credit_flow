import React from 'react';

export interface ToastProps {
  children?: React.ReactNode;
  /** @startingPoint section="Components" subtitle="Transient notification, 4 tones" viewport="700x140" */
  tone?: 'neutral' | 'success' | 'warning' | 'danger';
  onDismiss?: () => void;
}
