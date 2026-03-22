import { cn } from '../../lib/utils';
import { Step } from '../../lib/types';
import { motion } from 'framer-motion';

interface StepperProps {
  steps: {
    id: Step;
    label: string;
    description?: string;
  }[];
  currentStep: Step;
  onStepClick?: (step: Step) => void;
  className?: string;
}

const Stepper = ({
  steps,
  currentStep,
  onStepClick,
  className,
}: StepperProps) => {
  const getCurrentStepIndex = () => {
    return steps.findIndex(step => step.id === currentStep);
  };

  const isStepCompleted = (stepId: Step) => {
    const currentIndex = getCurrentStepIndex();
    const stepIndex = steps.findIndex(step => step.id === stepId);
    return stepIndex < currentIndex;
  };

  const isStepCurrent = (stepId: Step) => {
    return stepId === currentStep;
  };

  const isStepClickable = (stepId: Step) => {
    if (!onStepClick) return false;
    const stepIndex = steps.findIndex(step => step.id === stepId);
    const currentIndex = getCurrentStepIndex();
    return stepIndex <= currentIndex;
  };

  return (
    <div className={cn('w-full py-4', className)}>
      <div className="relative flex justify-between items-center w-full max-w-3xl mx-auto">
        {/* Connecting Line Background */}
        <div className="absolute top-1/2 left-0 w-full h-0.5 bg-neutral-800 -translate-y-1/2 rounded-full z-0" />
        
        {/* Connecting Line Active Progress */}
        <motion.div 
          className="absolute top-1/2 left-0 h-0.5 bg-gradient-to-r from-primary-600 to-secondary-mint -translate-y-1/2 rounded-full z-0 origin-left"
          initial={{ width: '0%' }}
          animate={{ width: `${(getCurrentStepIndex() / (steps.length - 1)) * 100}%` }}
          transition={{ duration: 0.5, ease: "easeInOut" }}
        />

        {steps.map((step, index) => {
          const isCompleted = isStepCompleted(step.id);
          const isCurrent = isStepCurrent(step.id);
          const isClickable = isStepClickable(step.id);
          
          return (
            <div
              key={step.id}
              className="relative z-10 flex flex-col items-center"
            >
              <motion.button
                type="button"
                onClick={() => isClickable && onStepClick?.(step.id)}
                disabled={!isClickable}
                className={cn(
                  'w-4 h-4 rounded-full border-2 transition-all duration-300 outline-none ring-offset-2 ring-offset-neutral-900 focus:ring-2 focus:ring-primary-500',
                  isCompleted || isCurrent 
                    ? 'bg-neutral-900 border-primary-500 shadow-[0_0_10px_rgba(58,111,248,0.5)]' 
                    : 'bg-neutral-900 border-neutral-600',
                  isClickable ? 'cursor-pointer' : 'cursor-default'
                )}
                animate={{
                  scale: isCurrent ? 1.5 : 1,
                  backgroundColor: isCompleted ? '#3A6FF8' : '#111418', // Primary or Dark
                  borderColor: isCompleted || isCurrent ? '#3A6FF8' : '#525252'
                }}
              />
              
              <div className="absolute top-8 left-1/2 -translate-x-1/2 whitespace-nowrap">
                <motion.span
                  className={cn(
                    'text-xs font-medium uppercase tracking-wider transition-colors duration-300',
                    isCurrent ? 'text-white font-bold' : isCompleted ? 'text-neutral-300' : 'text-neutral-600'
                  )}
                  animate={{ y: isCurrent ? 0 : 5, opacity: isCurrent || isCompleted ? 1 : 0.7 }}
                >
                  {step.label}
                </motion.span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default Stepper;
