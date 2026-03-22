import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card';
import Button from '../ui/Button';
import ProgressBar from '../ui/ProgressBar';
import { ArrowLeft, ArrowRight, Check, X, AlertTriangle, ThumbsUp, FileText } from 'lucide-react';
import { EvaluationResult } from '../../lib/types';
import { formatFitDecision, getFitDecisionColor } from '../../lib/utils';

interface EvaluationStepProps {
  evaluationResult: EvaluationResult;
  onBack: () => void;
  onContinue: () => void;
}

const EvaluationStep: React.FC<EvaluationStepProps> = ({
  evaluationResult,
  onBack,
  onContinue,
}) => {
  const { overallScore, categories, pros, cons, fitDecision, summary } = evaluationResult;
  
  const getFitDecisionIcon = () => {
    switch (fitDecision) {
      case 'excellent':
        return <ThumbsUp className="h-6 w-6 text-success-600" />;
      case 'good':
        return <Check className="h-6 w-6 text-primary-600" />;
      case 'moderate':
        return <AlertTriangle className="h-6 w-6 text-warning-500" />;
      case 'poor':
        return <X className="h-6 w-6 text-error-600" />;
      default:
        return null;
    }
  };

  return (
    <div className="animate-fade-in">
      <Card className="max-w-5xl mx-auto shadow-xl border-0 overflow-hidden">
        <div className="bg-gradient-to-r from-primary-600 to-primary-800 p-6 text-white">
          <div className="flex justify-between items-start md:items-center flex-col md:flex-row gap-4">
            <div>
              <h2 className="text-2xl font-bold text-white mb-1">Evaluation Report</h2>
              <p className="text-primary-100 text-sm">Comprehensive analysis of your resume against the job description</p>
            </div>
            <div className="flex items-center bg-white/10 backdrop-blur-md px-6 py-3 rounded-2xl border border-white/20 shadow-lg">
              <div className="mr-4 text-right">
                <div className="text-xs text-primary-100 uppercase tracking-wider font-semibold">Overall Match</div>
                <div className="text-3xl font-extrabold text-white leading-none">{overallScore}%</div>
              </div>
              <div className="h-12 w-12 rounded-full bg-white flex items-center justify-center shadow-inner">
                {overallScore >= 80 ? (
                   <ThumbsUp className="h-6 w-6 text-success-600" />
                ) : overallScore >= 60 ? (
                   <Check className="h-6 w-6 text-primary-600" />
                ) : (
                   <AlertTriangle className="h-6 w-6 text-warning-500" />
                )}
              </div>
            </div>
          </div>
        </div>
        
        <CardContent className="p-8 space-y-8">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8">
            {/* Left Column: Categories */}
            <div className="lg:col-span-5 space-y-6">
              <h3 className="text-lg font-bold text-white border-b border-white/10 pb-2">Category Breakdown</h3>
              <div className="space-y-5">
                {categories.map((category) => (
                  <div key={category.name} className="group">
                    <div className="flex justify-between items-end mb-1">
                      <span className="text-sm font-medium text-neutral-300 group-hover:text-primary-400 transition-colors">{category.name}</span>
                      <span className={`text-sm font-bold ${
                        category.score >= 80 ? 'text-green-400' : 
                        category.score >= 50 ? 'text-yellow-400' : 'text-red-400'
                      }`}>{category.score}%</span>
                    </div>
                    <div className="w-full bg-neutral-800 rounded-full h-2.5 overflow-hidden">
                      <div 
                        className={`h-2.5 rounded-full transition-all duration-1000 ease-out ${
                          category.score >= 80 ? 'bg-green-500' : 
                          category.score >= 50 ? 'bg-yellow-500' : 'bg-red-500'
                        }`} 
                        style={{ width: `${category.score}%` }}
                      ></div>
                    </div>
                    <p className="text-xs text-neutral-500 mt-1 leading-tight">{category.feedback}</p>
                  </div>
                ))}
              </div>
            </div>
            
            {/* Right Column: Assessment & Feedback */}
            <div className="lg:col-span-7 space-y-6">
              <div className="bg-neutral-800/50 rounded-xl p-6 border border-white/10 shadow-sm">
                <h3 className="text-lg font-bold text-white mb-3 flex items-center">
                  <FileText className="h-5 w-5 mr-2 text-primary-400" />
                  Assessment Summary
                </h3>
                <div className="flex items-start gap-3 mb-3">
                  <div className="mt-1">{getFitDecisionIcon()}</div>
                  <div>
                    <span className={`inline-block px-2 py-0.5 rounded text-xs font-bold uppercase mb-1 ${
                      fitDecision === 'excellent' || fitDecision === 'good' ? 'bg-green-500/20 text-green-400' :
                      fitDecision === 'moderate' ? 'bg-yellow-500/20 text-yellow-400' : 'bg-red-500/20 text-red-400'
                    }`}>
                      {formatFitDecision(fitDecision)}
                    </span>
                    <p className="text-sm text-neutral-300 leading-relaxed">{summary}</p>
                  </div>
                </div>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-green-500/5 rounded-xl p-5 border border-green-500/20">
                  <h4 className="text-sm font-bold text-green-400 flex items-center mb-3 uppercase tracking-wide">
                    <Check className="h-4 w-4 mr-1.5" /> Strengths
                  </h4>
                  <ul className="space-y-2">
                    {pros.map((pro, index) => (
                      <li key={index} className="flex items-start text-sm text-neutral-300">
                        <span className="mr-2 text-green-500 mt-1">•</span>
                        <span className="flex-1">{pro}</span>
                      </li>
                    ))}
                  </ul>
                </div>
                
                <div className="bg-red-500/5 rounded-xl p-5 border border-red-500/20">
                  <h4 className="text-sm font-bold text-red-400 flex items-center mb-3 uppercase tracking-wide">
                    <X className="h-4 w-4 mr-1.5" /> Areas for Improvement
                  </h4>
                  <ul className="space-y-2">
                    {cons.map((con, index) => (
                      <li key={index} className="flex items-start text-sm text-neutral-300">
                        <span className="mr-2 text-red-500 mt-1">•</span>
                        <span className="flex-1">{con}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </CardContent>
        
        <CardFooter className="flex justify-between">
          <Button
            variant="outline"
            onClick={onBack}
            icon={<ArrowLeft className="h-4 w-4" />}
            iconPosition="left"
          >
            Back
          </Button>
          
          <Button
            onClick={onContinue}
            icon={<ArrowRight className="h-4 w-4" />}
            iconPosition="right"
          >
            Generate Optimized Resume
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default EvaluationStep;
