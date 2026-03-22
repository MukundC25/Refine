import React from 'react';
import { cn } from '../../lib/utils';
import { motion, HTMLMotionProps } from 'framer-motion';

interface CardProps extends HTMLMotionProps<"div"> {
  children: React.ReactNode;
  variant?: 'default' | 'glass' | 'glass-dark';
  hoverEffect?: boolean;
}

const Card = React.forwardRef<HTMLDivElement, CardProps>(({
  children,
  className,
  variant = 'glass',
  hoverEffect = false,
  ...props
}, ref) => {
  const variantStyles = {
    default: 'bg-white shadow-xl rounded-xl border border-neutral-100',
    glass: 'glass-card rounded-xl',
    'glass-dark': 'bg-neutral-charcoal/80 backdrop-blur-md border border-white/10 shadow-xl rounded-xl',
  };

  return (
    <motion.div
      ref={ref}
      className={cn(
        variantStyles[variant],
        'overflow-hidden',
        className
      )}
      whileHover={hoverEffect ? { y: -5, transition: { duration: 0.2 } } : {}}
      {...props}
    >
      {children}
    </motion.div>
  );
});
Card.displayName = "Card";

interface CardHeaderProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const CardHeader = ({
  children,
  className,
  ...props
}: CardHeaderProps) => {
  return (
    <div
      className={cn('p-6 border-b border-white/5', className)}
      {...props}
    >
      {children}
    </div>
  );
};

interface CardTitleProps extends React.HTMLAttributes<HTMLHeadingElement> {
  children: React.ReactNode;
}

const CardTitle = ({
  children,
  className,
  ...props
}: CardTitleProps) => {
  return (
    <h3
      className={cn('text-xl font-display font-bold text-white', className)}
      {...props}
    >
      {children}
    </h3>
  );
};

interface CardDescriptionProps extends React.HTMLAttributes<HTMLParagraphElement> {
  children: React.ReactNode;
}

const CardDescription = ({
  children,
  className,
  ...props
}: CardDescriptionProps) => {
  return (
    <p
      className={cn('text-sm text-neutral-silver mt-2 leading-relaxed', className)}
      {...props}
    >
      {children}
    </p>
  );
};

interface CardContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const CardContent = ({
  children,
  className,
  ...props
}: CardContentProps) => {
  return (
    <div
      className={cn('p-6', className)}
      {...props}
    >
      {children}
    </div>
  );
};

interface CardFooterProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

const CardFooter = ({
  children,
  className,
  ...props
}: CardFooterProps) => {
  return (
    <div
      className={cn('p-6 border-t border-white/5', className)}
      {...props}
    >
      {children}
    </div>
  );
};

export { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter };
