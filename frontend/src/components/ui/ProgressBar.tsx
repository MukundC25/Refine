import React from 'react';
import { cn, getScoreColorClass, getScoreBgClass, formatScore } from '../../lib/utils';

interface ProgressBarProps {
  value: number;
  max?: number;
  showValue?: boolean;
  size?: 'sm' | 'md' | 'lg';
  label?: string;
  className?: string;
}

const ProgressBar = ({
  value,
  max = 100,
  showValue = true,
  size = 'md',
  label,
  className,
}: ProgressBarProps) => {
  const percentage = (value / max) * 100;
  
  // Size classes
  const sizeClasses = {
    sm: 'h-1.5',
    md: 'h-2.5',
    lg: 'h-4',
  };
  
  // Color based on value
  const colorClass = getScoreColorClass(percentage);
  // Use static Tailwind classes for background color
  let staticBgClass = "bg-green-400";
  if (percentage >= 80) staticBgClass = "bg-green-400";
  else if (percentage >= 60) staticBgClass = "bg-yellow-400";
  else staticBgClass = "bg-red-400";

  return (
    <div className={cn('w-full', className)}>
      {label && (
        <div className="flex justify-between items-center mb-1">
          <span className="text-sm font-medium text-gray-700">{label}</span>
          {showValue && <span className={cn('text-sm font-medium', colorClass)}>{formatScore(percentage)}</span>}
        </div>
      )}
      
      <div className={cn('w-full bg-gray-200 rounded-full overflow-hidden', sizeClasses[size])}>
        <div
          className={cn('transition-all duration-500 ease-out rounded-full', staticBgClass)}
          style={{ width: `${percentage}%` }}
          role="progressbar"
          aria-valuenow={value}
          aria-valuemin={0}
          aria-valuemax={max}
        />
      </div>
    </div>
  );
};

export default ProgressBar;
