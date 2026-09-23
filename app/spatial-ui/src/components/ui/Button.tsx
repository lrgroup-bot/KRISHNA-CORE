import type { ButtonHTMLAttributes } from 'react';
import { cn } from '../../lib/cn';

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'ghost';
};

export function Button({ className, variant = 'primary', ...props }: Props) {
  return (
    <button
      className={cn('kr-button', variant === 'ghost' && 'kr-button--ghost', className)}
      {...props}
    />
  );
}
