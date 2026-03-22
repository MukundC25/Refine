import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card';
import Button from '../ui/Button';
import { ArrowLeft, ArrowRight, FileEdit, Copy, Check, X, AlertTriangle, ThumbsUp } from 'lucide-react';
import { RefinementResult, EvaluationResult } from '../../lib/types';
import { formatFitDecision, getFitDecisionColor, formatScore } from '../../lib/utils';
import Markdown from 'react-markdown';

// Import Editor and syntax highlighting libraries
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs/components/prism-core';
import 'prismjs/components/prism-latex'; // Import LaTeX language
import 'prismjs/themes/prism.css'; // Import a basic theme

interface RefinementStepProps {
  refinementResult: RefinementResult;
  originalEvaluationResult: EvaluationResult | null;
  refinedEvaluationResult: EvaluationResult | null;
  onBack: () => void;
}

const RefinementStep: React.FC<RefinementStepProps> = ({
  refinementResult,
  originalEvaluationResult,
  refinedEvaluationResult,
  onBack,
}) => {
  const [copied, setCopied] = useState(false);

  const originalScore = originalEvaluationResult?.overallScore ?? 0;
  const refinedScore = refinedEvaluationResult?.overallScore ?? 0;
  const improvementScore = refinedScore - originalScore;

  const handleCopyToClipboard = async () => {
    try {
      await navigator.clipboard.writeText(refinementResult.refinedLatexCode);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      alert("Failed to copy to clipboard.");
    }
  };

  const getFitDecisionIcon = (fitDecision: EvaluationResult['fitDecision']) => {
    switch (fitDecision) {
      case 'excellent': return <ThumbsUp className="h-5 w-5 text-green-400" />;
      case 'good': return <Check className="h-5 w-5 text-primary-400" />;
      case 'moderate': return <AlertTriangle className="h-5 w-5 text-yellow-400" />;
      case 'poor': return <X className="h-5 w-5 text-red-400" />;
      default: return null;
    }
  };

  return (
    <div className="animate-fade-in">
      <Card className="max-w-6xl mx-auto border-0 shadow-xl overflow-hidden bg-neutral-900">
        {/* Header Banner */}
        <div className="bg-gradient-to-r from-primary-600 to-primary-800 p-8 text-white">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            <div>
              <h2 className="text-3xl font-display font-bold text-white mb-2">Optimized Resume</h2>
              <p className="text-primary-100">Review your enhanced resume and performance improvements</p>
            </div>
            {originalEvaluationResult && refinedEvaluationResult && (
               <div className="flex items-center gap-6 bg-white/10 backdrop-blur-md px-6 py-3 rounded-2xl border border-white/20 shadow-lg">
                 <div className="text-center">
                   <div className="text-xs text-primary-100 uppercase tracking-wider font-semibold mb-1">Original</div>
                   <div className="text-2xl font-bold text-white/80">{formatScore(originalScore)}</div>
                 </div>
                 <ArrowRight className="h-6 w-6 text-white/60" />
                 <div className="text-center">
                   <div className="text-xs text-white uppercase tracking-wider font-semibold mb-1">Refined</div>
                   <div className="text-4xl font-extrabold text-white">{formatScore(refinedScore)}</div>
                 </div>
                 {improvementScore > 0 && (
                   <div className="flex items-center px-3 py-1 rounded-full text-sm font-bold bg-white text-primary-700">
                      +{formatScore(improvementScore)}
                   </div>
                 )}
               </div>
            )}
          </div>
        </div>

        <CardContent className="p-8 bg-neutral-900">
          <div className="space-y-8">
            {/* Improvement Summary */}
            <div className="bg-neutral-800/50 rounded-xl p-6 border border-primary-500/20 shadow-sm">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center">
                <div className="bg-primary-500/20 p-2 rounded-lg mr-3">
                   <Check className="h-5 w-5 text-primary-400" />
                </div>
                Key Improvements
              </h3>
              <div className="prose prose-invert max-w-none text-neutral-300 text-sm leading-relaxed">
                <Markdown>{refinementResult.overallImprovementsSummary || "The AI has optimized your content for better alignment."}</Markdown>
              </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
               {/* Refined Resume Editor */}
               <div className="flex flex-col h-full">
                  <div className="bg-white/5 rounded-t-xl border border-white/10 border-b-0 px-5 py-4 flex justify-between items-center">
                    <h3 className="font-bold text-white flex items-center">
                      <FileEdit className="h-5 w-5 mr-2 text-primary-400" />
                      Optimized LaTeX Code
                    </h3>
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={handleCopyToClipboard}
                      className={copied ? "bg-green-500/20 text-green-400 border-green-500/30" : "border-white/20 text-neutral-300 hover:text-white"}
                    >
                      {copied ? <Check className="h-4 w-4 mr-2" /> : <Copy className="h-4 w-4 mr-2" />}
                      {copied ? "Copied!" : "Copy Code"}
                    </Button>
                  </div>
                  <div className="border border-white/10 rounded-b-xl bg-black/40 h-[600px] overflow-hidden shadow-inner group relative">
                     <div className="absolute inset-0 overflow-y-auto scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent p-1">
                        <Editor
                          value={refinementResult.refinedLatexCode || 'No LaTeX code provided.'}
                          highlight={code => highlight(code, languages.latex, 'latex')}
                          padding={20}
                          style={{
                            fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                            fontSize: 13,
                            backgroundColor: 'transparent',
                            minHeight: '100%',
                            color: '#e5e7eb'
                          }}
                          className="min-h-[600px]"
                          readOnly
                          onValueChange={() => {}}
                        />
                     </div>
                  </div>
               </div>

               {/* Evaluation & Analysis Side */}
               <div className="space-y-6">
                 <div className="bg-neutral-800/30 rounded-xl border border-white/10 p-6 shadow-sm h-full">
                    <h3 className="text-lg font-bold text-white mb-6 border-b border-white/10 pb-4">Performance Analysis</h3>
                    
                    {refinedEvaluationResult && (
                      <div className="space-y-6">
                        <div>
                          <h4 className="text-xs uppercase tracking-wider text-neutral-500 font-semibold mb-4">Category Performance</h4>
                          <div className="space-y-4">
                            {refinedEvaluationResult.categories.map((category) => (
                              <div key={category.name}>
                                <div className="flex justify-between text-sm mb-1">
                                  <span className="font-medium text-neutral-300">{category.name}</span>
                                  <span className={`font-bold ${
                                    category.score >= 80 ? 'text-green-400' : 
                                    category.score >= 60 ? 'text-yellow-400' : 'text-red-400'
                                  }`}>{category.score}%</span>
                                </div>
                                <div className="w-full bg-neutral-700 rounded-full h-1.5">
                                  <div 
                                    className={`h-1.5 rounded-full ${
                                      category.score >= 80 ? 'bg-green-500' : 
                                      category.score >= 60 ? 'bg-yellow-500' : 'bg-red-500'
                                    }`} 
                                    style={{ width: `${category.score}%` }}
                                  ></div>
                                </div>
                              </div>
                            ))}
                          </div>
                        </div>

                        <div className="pt-4 border-t border-white/10">
                           <h4 className="text-xs uppercase tracking-wider text-neutral-500 font-semibold mb-3">Final Verdict</h4>
                           <div className="flex items-start gap-3 bg-white/5 p-4 rounded-lg border border-white/5">
                              <div className="mt-0.5">{getFitDecisionIcon(refinedEvaluationResult.fitDecision)}</div>
                              <div>
                                <div className={`font-bold ${getFitDecisionColor(refinedEvaluationResult.fitDecision)} mb-1`}>
                                  {formatFitDecision(refinedEvaluationResult.fitDecision)}
                                </div>
                                <p className="text-sm text-neutral-400 leading-relaxed">{refinedEvaluationResult.summary}</p>
                              </div>
                           </div>
                        </div>
                      </div>
                    )}
                 </div>
               </div>
            </div>
          </div>
        </CardContent>
        
        <CardFooter className="flex justify-between bg-neutral-900 border-t border-white/5">
          <Button
            variant="outline"
            onClick={onBack}
            icon={<ArrowLeft className="h-4 w-4" />}
            iconPosition="left"
          >
            Back
          </Button>
          
          <Button
            onClick={handleCopyToClipboard}
            icon={<Copy className="h-4 w-4" />}
            iconPosition="left"
            disabled={!refinementResult.refinedLatexCode}
          >
            {copied ? "Copied to Clipboard!" : "Copy to Clipboard"}
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default RefinementStep;
