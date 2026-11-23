import React from 'react';

export interface TabItem {
  value: string;
  label: string;
}

export interface TabsProps {
  /** @startingPoint section="Components" subtitle="Underline tabs with accent-orange active state" viewport="700x100" */
  tabs?: TabItem[];
  value?: string;
  onChange?: (value: string) => void;
}
