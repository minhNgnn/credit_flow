import React from 'react';

export interface CheckboxProps {
  label?: string;
  checked?: boolean;
  /** @startingPoint section="Components" subtitle="Checkbox with custom checkmark" viewport="700x120" */
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
}
