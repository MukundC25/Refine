import React from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card';
import Button from '../ui/Button';
import { ArrowLeft, ArrowRight, FileText } from 'lucide-react';

// Import Editor and syntax highlighting libraries
import Editor from 'react-simple-code-editor';
import { highlight, languages } from 'prismjs/components/prism-core';
import 'prismjs/components/prism-latex'; // Import LaTeX language
import 'prismjs/themes/prism.css'; // Import a basic theme

interface PreviewStepProps {
  resumeText: string;
  jobDescription: string;
  onBack: () => void;
  onContinue: () => void;
}

const PreviewStep: React.FC<PreviewStepProps> = ({
  resumeText,
  jobDescription,
  onBack,
  onContinue,
}) => {
  return (
    <div className="animate-fade-in">
      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <CardTitle>Preview & Confirm</CardTitle>
          <CardDescription>
            Review your LaTeX resume code and job description before analysis
          </CardDescription>
        </CardHeader>
        
        <CardContent className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            <div className="flex flex-col h-full">
              <div className="bg-white/5 rounded-t-xl border border-b-0 border-white/10 px-4 py-3 flex items-center justify-between backdrop-blur-sm">
                <h3 className="text-sm font-semibold text-white flex items-center uppercase tracking-wider">
                  <FileText className="h-4 w-4 mr-2 text-primary-400" />
                  Resume (LaTeX)
                </h3>
                <span className="text-xs text-neutral-400 bg-white/5 px-2 py-1 rounded border border-white/10">Read-only</span>
              </div>
              <div className="border border-white/10 rounded-b-xl bg-neutral-900/50 flex-grow overflow-hidden relative group">
                <div className="absolute inset-0 overflow-y-auto scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent p-1">
                  <Editor
                    value={resumeText || 'No LaTeX code provided.'}
                    highlight={code => highlight(code, languages.latex, 'latex')}
                    padding={16}
                    style={{
                      fontFamily: '"JetBrains Mono", "Fira Code", monospace',
                      fontSize: 13,
                      backgroundColor: 'transparent',
                      minHeight: '100%',
                      color: '#e2e8f0' // Text color for editor
                    }}
                    className="min-h-[500px]"
                    readOnly
                    onValueChange={() => {}}
                  />
                </div>
              </div>
            </div>
            
            <div className="flex flex-col h-full">
              <div className="bg-white/5 rounded-t-xl border border-b-0 border-white/10 px-4 py-3 backdrop-blur-sm">
                <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Target Job Description</h3>
              </div>
              <div className="border border-white/10 rounded-b-xl bg-neutral-900/50 p-5 h-[500px] overflow-y-auto scrollbar-thin scrollbar-thumb-white/20 scrollbar-track-transparent shadow-inner">
                <div className="prose prose-sm max-w-none text-neutral-300 leading-relaxed prose-invert">
                  {jobDescription ? (
                    <pre className="whitespace-pre-wrap font-sans text-sm bg-transparent text-neutral-300">{jobDescription}</pre>
                  ) : (
                    <p className="text-neutral-500 italic">No job description provided.</p>
                  )}
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
            Analyze Resume
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default PreviewStep;
