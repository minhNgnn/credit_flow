import React from 'react';

export interface RadioProps {
  label?: string;
  checked?: boolean;
  /** @startingPoint section="Components" subtitle="Radio button, single-select groups" viewport="700x120" */
  onChange?: () => void;
  disabled?: boolean;
  name?: string;
}
