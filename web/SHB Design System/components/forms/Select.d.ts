import React from 'react';

export interface SelectOption {
  value: string;
  label: string;
}

export interface SelectProps {
  label?: string;
  value?: string;
  onChange?: (e: React.ChangeEvent<HTMLSelectElement>) => void;
  /** @startingPoint section="Components" subtitle="Native dropdown, styled to match Input" viewport="700x160" */
  options?: SelectOption[];
  disabled?: boolean;
  hint?: string;
}
