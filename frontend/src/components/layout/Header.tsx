import React, { useState, useEffect } from 'react';
import { FileText, Menu, X, User as UserIcon, LogOut } from 'lucide-react';
import Button from '../ui/Button';
import { motion, AnimatePresence } from 'framer-motion';
import { cn } from '../../lib/utils';
import { User, Step } from '../../lib/types';

interface HeaderProps {
  onStart?: () => void;
  onLogoClick?: () => void;
  user?: User | null;
  onLoginClick?: () => void;
  onLogout?: () => void;
  onProfileClick?: () => void;
  mode?: 'landing' | 'app';
  currentStep?: Step;
  onStepClick?: (step: Step) => void;
}

const Header: React.FC<HeaderProps> = ({ 
  onStart, 
  onLogoClick,
  user, 
  onLoginClick, 
  onLogout, 
  onProfileClick, 
  mode = 'landing',
  currentStep,
  onStepClick
}) => {
  const [isScrolled, setIsScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);
    };
    window.addEventListener('scroll', handleScroll);
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const landingLinks = [
    { name: 'Features', href: '#features' },
    { name: 'How it Works', href: '#how-it-works' },
    { name: 'FAQ', href: '#faq' },
  ];

  const appSteps: { id: Step; label: string }[] = [
    { id: 'upload', label: 'Upload' },
    { id: 'preview', label: 'Preview' },
    { id: 'evaluation', label: 'Evaluation' },
    { id: 'refinement', label: 'Refinement' },
  ];

  return (
    <header 
      className={cn(
        "fixed top-0 left-0 right-0 z-50 transition-all duration-300 border-b",
        isScrolled 
          ? "bg-neutral-charcoal/80 backdrop-blur-md border-white/10 py-4" 
          : "bg-transparent border-transparent py-6"
      )}
    >
      <div className="max-w-7xl mx-auto px-6">
        <div className="flex justify-between items-center">
          {/* Logo */}
          <button 
            onClick={onLogoClick}
            className="flex items-center space-x-3 hover:opacity-80 transition-opacity cursor-pointer"
          >
            <div className="bg-gradient-to-br from-primary-500 to-primary-700 p-2 rounded-xl shadow-lg shadow-primary-500/20">
              <FileText className="h-6 w-6 text-white" />
            </div>
            <div className="text-2xl font-display font-bold text-white tracking-tight">
              Refine
            </div>
          </button>
          
          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-8">
            {mode === 'landing' ? (
              landingLinks.map((link) => (
                <a 
                  key={link.name} 
                  href={link.href}
                  className="text-sm font-medium text-neutral-silver/70 hover:text-white transition-colors"
                >
                  {link.name}
                </a>
              ))
            ) : (
              appSteps.map((step) => (
                <button
                  key={step.id}
                  onClick={() => onStepClick && onStepClick(step.id)}
                  className={cn(
                    "text-sm font-medium transition-colors",
                    currentStep === step.id 
                      ? "text-white font-bold" 
                      : "text-neutral-silver/50 hover:text-neutral-silver"
                  )}
                  disabled={!onStepClick} // Or implement validation logic
                >
                  {step.label.toUpperCase()}
                </button>
              ))
            )}
          </nav>

          {/* Desktop CTA */}
          <div className="hidden md:flex items-center gap-4">
            {user ? (
                <div className="flex items-center gap-4">
                    <button 
                        onClick={onProfileClick}
                        className="text-sm font-medium text-white flex items-center gap-2 hover:text-primary-400 transition-colors"
                    >
                        {user.picture ? (
                            <img src={user.picture} alt={user.full_name || user.email} className="w-6 h-6 rounded-full" />
                        ) : (
                            <UserIcon className="w-4 h-4" />
                        )}
                        {user.full_name || user.email}
                    </button>
                    <Button size="sm" variant="outline" onClick={onLogout}>
                        <LogOut className="w-4 h-4 mr-2" />
                        Logout
                    </Button>
                </div>
            ) : (
                <>
                    <button 
                        onClick={onLoginClick} 
                        className="text-sm font-medium text-white hover:text-primary-400 transition-colors"
                    >
                        Log In
                    </button>
                    <Button size="sm" glow onClick={onStart}>Get Started</Button>
                </>
            )}
          </div>

          {/* Mobile Menu Toggle */}
          <button 
            className="md:hidden text-white p-2"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          >
            {mobileMenuOpen ? <X /> : <Menu />}
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="md:hidden bg-neutral-charcoal border-b border-white/10 overflow-hidden"
          >
            <div className="flex flex-col p-6 space-y-4">
              {mode === 'landing' ? (
                landingLinks.map((link) => (
                  <a 
                    key={link.name} 
                    href={link.href}
                    className="text-base font-medium text-neutral-silver/80 hover:text-white py-2 border-b border-white/5"
                    onClick={() => setMobileMenuOpen(false)}
                  >
                    {link.name}
                  </a>
                ))
              ) : (
                 appSteps.map((step) => (
                  <button
                    key={step.id}
                    onClick={() => {
                        if(onStepClick) onStepClick(step.id);
                        setMobileMenuOpen(false);
                    }}
                    className={cn(
                      "text-base font-medium text-left py-2 border-b border-white/5",
                      currentStep === step.id 
                        ? "text-white" 
                        : "text-neutral-silver/50"
                    )}
                  >
                    {step.label}
                  </button>
                ))
              )}
              <div className="pt-4 flex flex-col gap-3">
                {user ? (
                    <Button variant="outline" fullWidth onClick={onLogout}>Logout</Button>
                ) : (
                    <Button variant="outline" fullWidth onClick={onLoginClick}>Log In</Button>
                )}
                <Button fullWidth glow onClick={() => {
                  setMobileMenuOpen(false);
                  if (onStart) onStart();
                }}>Get Started</Button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </header>
  );
};

export default Header;
