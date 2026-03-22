import React from 'react';
import { cn } from '../../lib/utils';

interface SectionProps extends React.HTMLAttributes<HTMLElement> {
  children: React.ReactNode;
  className?: string;
  id?: string;
  fullWidth?: boolean;
}

const Section = ({
  children,
  className,
  id,
  fullWidth = false,
  ...props
}: SectionProps) => {
  return (
    <section
      id={id}
      className={cn('relative py-16 md:py-24 overflow-hidden', className)}
      {...props}
    >
      <div className={cn(
        'mx-auto px-6 md:px-8', 
        fullWidth ? 'w-full max-w-none' : 'max-w-7xl'
      )}>
        {children}
      </div>
    </section>
  );
};

export default Section;
