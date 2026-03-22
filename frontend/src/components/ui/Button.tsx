import React from 'react';
import { cn } from '../../lib/utils';
import { motion, HTMLMotionProps } from 'framer-motion';

type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'ghost' | 'link' | 'glass';
type ButtonSize = 'sm' | 'md' | 'lg';

// Combine Framer Motion props with standard button props
interface ButtonProps extends Omit<HTMLMotionProps<"button">, "children"> {
  children: React.ReactNode;
  variant?: ButtonVariant;
  size?: ButtonSize;
  isLoading?: boolean;
  fullWidth?: boolean;
  icon?: React.ReactNode;
  iconPosition?: 'left' | 'right';
  glow?: boolean;
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({
    children,
    className,
    variant = 'primary',
    size = 'md',
    isLoading = false,
    fullWidth = false,
    icon,
    iconPosition = 'left',
    disabled,
    glow = false,
    ...props
  }, ref) => {
    // Base styles
    const baseStyles = 'inline-flex items-center justify-center rounded-lg font-medium transition-all duration-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-2 disabled:opacity-50 disabled:pointer-events-none relative overflow-hidden';
    
    // Variant styles
    const variantStyles = {
      primary: 'bg-primary hover:bg-primary-600 text-white shadow-lg shadow-primary/25 border border-primary/50',
      secondary: 'bg-secondary-mint text-neutral-900 hover:bg-secondary-mint/90 shadow-lg shadow-secondary-mint/25',
      outline: 'border border-glass-border bg-transparent hover:bg-glass-highlight text-white',
      ghost: 'bg-transparent hover:bg-white/5 text-neutral-300 hover:text-white',
      link: 'bg-transparent underline-offset-4 hover:underline text-primary-400 hover:text-primary-300',
      glass: 'glass-button text-white hover:text-white',
    };
    
    // Size styles
    const sizeStyles = {
      sm: 'text-xs px-3 py-1.5 h-8',
      md: 'text-sm px-5 py-2.5 h-11',
      lg: 'text-base px-8 py-3.5 h-14',
    };
    
    // Width style
    const widthStyle = fullWidth ? 'w-full' : '';

    // Glow effect
    const glowStyle = glow ? 'shadow-glow-primary' : '';
    
    return (
      <motion.button
        ref={ref}
        className={cn(
          baseStyles,
          variantStyles[variant],
          sizeStyles[size],
          widthStyle,
          glowStyle,
          className
        )}
        disabled={isLoading || disabled}
        whileHover={{ scale: disabled ? 1 : 1.02 }}
        whileTap={{ scale: disabled ? 1 : 0.98 }}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-1 mr-2 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            ></circle>
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            ></path>
          </svg>
        )}
        
        {icon && iconPosition === 'left' && !isLoading && (
          <span className="mr-2">{icon}</span>
        )}
        
        {children}
        
        {icon && iconPosition === 'right' && (
          <span className="ml-2">{icon}</span>
        )}
      </motion.button>
    );
  }
);

Button.displayName = 'Button';

export default Button;
