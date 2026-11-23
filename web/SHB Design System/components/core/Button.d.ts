import React from 'react';

export interface ButtonProps {
  children?: React.ReactNode;
  /** @startingPoint section="Components" subtitle="Primary CTA button, 3 sizes, 5 variants" viewport="700x220" */
  variant?: 'primary' | 'accent' | 'secondary' | 'ghost' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  icon?: React.ReactNode;
  onClick?: () => void;
  type?: 'button' | 'submit';
}
