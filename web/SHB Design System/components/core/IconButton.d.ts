import React from 'react';

export interface IconButtonProps {
  icon: React.ReactNode;
  label: string;
  size?: 'sm' | 'md' | 'lg';
  variant?: 'ghost' | 'solid' | 'outline';
  onClick?: () => void;
  disabled?: boolean;
}
