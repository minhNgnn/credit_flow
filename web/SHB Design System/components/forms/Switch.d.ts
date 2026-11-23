import React from 'react';

export interface SwitchProps {
  checked?: boolean;
  /** @startingPoint section="Components" subtitle="Toggle switch for settings" viewport="700x120" */
  onChange?: (checked: boolean) => void;
  disabled?: boolean;
  label?: string;
}
