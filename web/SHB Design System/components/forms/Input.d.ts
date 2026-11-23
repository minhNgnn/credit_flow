import React from 'react';

export interface InputProps {
  label?: string;
  placeholder?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLInputElement>) => void;
  type?: string;
  disabled?: boolean;
  error?: string;
  /** @startingPoint section="Components" subtitle="Text field with label, hint, and error states" viewport="700x260" */
  hint?: string;
  size?: 'sm' | 'md' | 'lg';
}
