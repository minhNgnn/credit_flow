import React from 'react';

export interface DialogProps {
  open?: boolean;
  title?: string;
  children?: React.ReactNode;
  /** @startingPoint section="Components" subtitle="Modal dialog with overlay, header, footer" viewport="700x360" */
  onClose?: () => void;
  footer?: React.ReactNode;
}
