import { useState, useEffect } from 'react';
import Header from './components/layout/Header';
import Footer from './components/layout/Footer';
import Stepper from './components/ui/Stepper';
import UploadStep from './components/steps/UploadStep';
import PreviewStep from './components/steps/PreviewStep';
import EvaluationStep from './components/steps/EvaluationStep';
import RefinementStep from './components/steps/RefinementStep';
import LandingPage from './components/landing/LandingPage';
import LoginModal from './components/auth/LoginModal';
import ProfileModal from './components/auth/ProfileModal';
import { AppState, Step, EvaluationResult, RefinementResult, User } from './lib/types';
import { evaluateResume, refineResume } from './lib/utils';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from './components/ui/Card';
import Button from './components/ui/Button';
import { Lock, CreditCard } from 'lucide-react';
import { jwtDecode } from 'jwt-decode';

function App() {
  const [view, setView] = useState<'landing' | 'app'>('landing');
  const [state, setState] = useState<AppState>({
    user: null,
    currentStep: 'upload',
    originalResume: null,
    jobDescription: '',
    evaluationResult: null,
    refinementResult: null,
    refinedEvaluationResult: null,
    isLoading: false,
    error: null,
  });

  const [loginModalOpen, setLoginModalOpen] = useState(false);
  const [profileModalOpen, setProfileModalOpen] = useState(false);

  // Mock User State (Payment related)
  const [usageCount, setUsageCount] = useState(0);
  const [isPro, setIsPro] = useState(false);
  const [showPaymentModal, setShowPaymentModal] = useState(false);
  const [paymentType, setPaymentType] = useState<'credit' | 'pro'>('credit');

  useEffect(() => {
    const storedUsage = localStorage.getItem('refine_usage_count');
    const storedPro = localStorage.getItem('refine_is_pro');
    const token = localStorage.getItem('refine_token');

    if (storedUsage) setUsageCount(parseInt(storedUsage, 10));
    if (storedPro === 'true') setIsPro(true);

    if (token) {
        fetchUser(token);
    }
  }, []);

  const fetchUser = async (token: string) => {
      try {
          const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
          const response = await fetch(`${API_BASE}/users/me`, {
              headers: { Authorization: `Bearer ${token}` }
          });
          if (response.ok) {
              const user = await response.json();
              setState(prev => ({ ...prev, user }));
          } else {
              localStorage.removeItem('refine_token');
          }
      } catch (e) {
          localStorage.removeItem('refine_token');
      }
  };

  const handleLoginSuccess = (token: string) => {
      localStorage.setItem('refine_token', token);
      fetchUser(token);
  };

  const handleLogout = () => {
      localStorage.removeItem('refine_token');
      setState(prev => ({ ...prev, user: null }));
      setView('landing');
  };
  
  const handleUserUpdate = (updatedUser: User) => {
      setState(prev => ({ ...prev, user: updatedUser }));
  };

  const incrementUsage = () => {
    const newCount = usageCount + 1;
    setUsageCount(newCount);
    localStorage.setItem('refine_usage_count', newCount.toString());
  };

  const handlePaymentSuccess = () => {
    if (paymentType === 'pro') {
      setIsPro(true);
      localStorage.setItem('refine_is_pro', 'true');
      alert("Upgraded to Pro! You have 15 uses per month.");
    } else {
      const newCount = Math.max(0, usageCount - 1);
      setUsageCount(newCount);
      localStorage.setItem('refine_usage_count', newCount.toString());
      alert("Credit added! You can optimize another resume.");
    }
    setShowPaymentModal(false);
  };

  const steps: { id: Step; label: string }[] = [
    { id: 'upload', label: 'Upload' },
    { id: 'preview', label: 'Preview' },
    { id: 'evaluation', label: 'Evaluation' },
    { id: 'refinement', label: 'Refinement' },
  ];

  const navigateToStep = (step: Step) => {
    if (canNavigateToStep(step)) {
      setState(prev => ({ ...prev, currentStep: step }));
    }
  };

  const canNavigateToStep = (step: Step): boolean => {
    const stepIndex = steps.findIndex(s => s.id === step);
    const currentStepIndex = steps.findIndex(s => s.id === state.currentStep);
    return stepIndex <= currentStepIndex + 1;
  };

  const handleUploadComplete = (latexCode: string, _resumeFile: File | null, jobDescription: string) => {
    setState(prev => ({
      ...prev,
      originalResume: { latexCode },
      jobDescription,
      currentStep: 'preview',
      evaluationResult: null,
      error: null,
    }));
  };

  const checkUsageLimit = () => {
    if (state.user?.is_admin || state.user?.is_pro || isPro) {
        return true;
    }
    
    if (usageCount >= 1) {
      setPaymentType('credit');
      setShowPaymentModal(true);
      return false;
    }
    
    return true;
  };

  const handleEvaluateResume = async () => {
    if (!state.originalResume) return;
    
    if (!checkUsageLimit()) return;

    setState(prev => ({
      ...prev,
      isLoading: true,
      error: null,
    }));
    try {
      const result = await evaluateResume(
        state.originalResume.latexCode,
        state.jobDescription
      );
      
      incrementUsage(); 

      setState(prev => ({
        ...prev,
        evaluationResult: result as EvaluationResult,
        currentStep: 'evaluation',
        isLoading: false,
      }));
    } catch (err) {
      setState(prev => ({
        ...prev,
        error: 'Failed to evaluate resume. Please try again.',
        isLoading: false,
      }));
    }
  };

  const handleRefineResume = async () => {
    if (!state.originalResume || !state.evaluationResult) return;
    
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    
    try {
      const result = await refineResume(
        state.originalResume.latexCode,
        state.jobDescription,
        state.evaluationResult
      );
      
      const refinedEvalResult = await evaluateResume(
        result.refinedLatexCode,
        state.jobDescription
      );

      setState(prev => ({
        ...prev,
        refinementResult: result as RefinementResult,
        refinedEvaluationResult: refinedEvalResult as EvaluationResult,
        currentStep: 'refinement',
        isLoading: false,
      }));

    } catch (error) {
      setState(prev => ({
        ...prev,
        error: 'Failed to refine or re-evaluate resume. Please try again.',
        isLoading: false,
      }));
    }
  };

  const renderStep = () => {
    switch (state.currentStep) {
      case 'upload':
        return (
            <UploadStep 
                onComplete={handleUploadComplete} 
                savedResume={state.user?.resume_latex}
            />
        );
      
      case 'preview':
        return (
          <PreviewStep
            resumeText={state.originalResume?.latexCode || ''}
            jobDescription={state.jobDescription}
            onBack={() => navigateToStep('upload')}
            onContinue={handleEvaluateResume}
          />
        );
      
      case 'evaluation':
        return (
          <EvaluationStep
            evaluationResult={state.evaluationResult!}
            onBack={() => navigateToStep('preview')}
            onContinue={handleRefineResume}
          />
        );
      
      case 'refinement':
        return (
          <RefinementStep
            refinementResult={state.refinementResult!}
            originalEvaluationResult={state.evaluationResult}
            refinedEvaluationResult={state.refinedEvaluationResult}
            onBack={() => navigateToStep('evaluation')}
          />
        );
      
      default:
        return null;
    }
  };

  const switchToApp = () => {
    if (!state.user) {
        setLoginModalOpen(true);
        setView('app'); 
        window.scrollTo(0, 0);
    } else {
        setView('app');
        window.scrollTo(0, 0);
    }
  };

  const handleLogoClick = () => {
    setView('landing');
    window.scrollTo(0, 0);
  };

  return (
    <div className={`flex flex-col min-h-screen ${view === 'landing' ? 'bg-neutral-charcoal' : 'bg-neutral-900 text-neutral-silver'}`}>
        <Header 
            onStart={switchToApp}
            onLogoClick={handleLogoClick}
            user={state.user} 
            onLoginClick={() => setLoginModalOpen(true)}
            onLogout={handleLogout}
            onProfileClick={() => setProfileModalOpen(true)}
            mode={view === 'landing' ? 'landing' : 'app'}
            currentStep={state.currentStep}
            onStepClick={view === 'app' ? navigateToStep : undefined}
        />
        
        {view === 'landing' ? (
            <>
                <LandingPage onStart={switchToApp} />
                <Footer onLogoClick={handleLogoClick} />
            </>
        ) : (
            <>
                <main className="flex-1 px-4 py-8 pt-24">
                    <div className="max-w-7xl mx-auto">
                    <Stepper
                        steps={steps}
                        currentStep={state.currentStep}
                        onStepClick={navigateToStep}
                        className="mb-8"
                    />
                    
                    {state.error && (
                        <div className="max-w-4xl mx-auto mb-6 p-4 bg-red-500/10 border border-red-500/20 rounded-md text-red-400">
                        {state.error}
                        </div>
                    )}
                    
                    {state.isLoading ? (
                        <div className="max-w-4xl mx-auto p-12 flex flex-col items-center justify-center">
                        <div className="w-12 h-12 border-4 border-primary-500/30 border-t-primary-500 rounded-full animate-spin mb-4"></div>
                        <p className="text-neutral-400">
                            {state.currentStep === 'preview' ? 'Analyzing your resume...' : 'Generating optimized resume...'}
                        </p>
                        </div>
                    ) : (
                        renderStep()
                    )}
                    </div>
                </main>
                <Footer onLogoClick={handleLogoClick} />
            </>
        )}
        
        <LoginModal 
            isOpen={loginModalOpen} 
            onClose={() => setLoginModalOpen(false)}
            onLoginSuccess={handleLoginSuccess}
        />
        
        {state.user && (
            <ProfileModal
                isOpen={profileModalOpen}
                onClose={() => setProfileModalOpen(false)}
                user={state.user}
                onUpdate={handleUserUpdate}
            />
        )}

        {/* Payment Modal */}
        {showPaymentModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
            <Card className="max-w-md w-full bg-neutral-900 border-primary-500/30 shadow-2xl">
                <CardHeader>
                <div className="w-12 h-12 rounded-full bg-primary-500/20 flex items-center justify-center mb-4 mx-auto text-primary-500">
                    <Lock size={24} />
                </div>
                <CardTitle className="text-center text-white">Usage Limit Reached</CardTitle>
                <CardDescription className="text-center text-neutral-400">
                    You've used your free optimization. Upgrade to continue.
                </CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                <div 
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${paymentType === 'credit' ? 'border-primary-500 bg-primary-500/10' : 'border-white/10 hover:border-white/30'}`}
                    onClick={() => setPaymentType('credit')}
                >
                    <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-white">1 Credit</span>
                    <span className="font-bold text-primary-400">₹10</span>
                    </div>
                    <p className="text-xs text-neutral-400">One-time use for a single resume</p>
                </div>
                
                <div 
                    className={`p-4 rounded-xl border cursor-pointer transition-all ${paymentType === 'pro' ? 'border-primary-500 bg-primary-500/10' : 'border-white/10 hover:border-white/30'}`}
                    onClick={() => setPaymentType('pro')}
                >
                    <div className="flex justify-between items-center mb-1">
                    <span className="font-bold text-white">Pro Plan</span>
                    <span className="font-bold text-primary-400">₹60/mo</span>
                    </div>
                    <p className="text-xs text-neutral-400">15 uses per month + priority access</p>
                </div>
                </CardContent>
                <CardFooter className="flex flex-col gap-3">
                <Button fullWidth onClick={handlePaymentSuccess} glow>
                    <CreditCard className="mr-2 h-4 w-4" />
                    Pay {paymentType === 'credit' ? '₹10' : '₹60'}
                </Button>
                <Button variant="ghost" fullWidth onClick={() => setShowPaymentModal(false)}>
                    Cancel
                </Button>
                </CardFooter>
            </Card>
            </div>
        )}
        
    </div>
  );
}

export default App;
