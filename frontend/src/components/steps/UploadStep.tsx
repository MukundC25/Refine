import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from '../ui/Card';
import FileUpload from '../ui/FileUpload';
import TextArea from '../ui/TextArea';
import Button from '../ui/Button';
import { Upload, ClipboardCheck, ArrowRight } from 'lucide-react';

interface UploadStepProps {
  onComplete: (resumeText: string, resumeFile: File | null, jobDescription: string) => void;
  savedResume?: string;
}

const UploadStep: React.FC<UploadStepProps> = ({ onComplete, savedResume }) => {
  const [resumeText, setResumeText] = useState(savedResume || '');
  const [resumeFile, setResumeFile] = useState<File | null>(null);
  const [jobDescription, setJobDescription] = useState('');
  const [uploadType, setUploadType] = useState<'file' | 'text'>('text');
  const [errors, setErrors] = useState<{ resume?: string; jobDescription?: string }>({});

  const handleResumeFileSelect = (file: File) => {
    setResumeFile(file);
    // Read .tex file content as string
    const reader = new FileReader();
    reader.onload = (e) => {
      setResumeText(e.target?.result as string || "");
    };
    reader.readAsText(file);
  };

  const validateForm = () => {
    const newErrors: { resume?: string; jobDescription?: string } = {};
    
    if (uploadType === 'file' && !resumeFile) {
      newErrors.resume = 'Please upload your resume';
    } else if (uploadType === 'text' && !resumeText.trim()) {
      newErrors.resume = 'Please enter your resume text';
    }
    
    if (!jobDescription.trim()) {
      newErrors.jobDescription = 'Please enter the job description';
    }
    
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = () => {
    if (validateForm()) {
      onComplete(resumeText, resumeFile, jobDescription);
    }
  };

  return (
    <div className="animate-fade-in">
      <Card className="max-w-4xl mx-auto">
        <CardHeader>
          <CardTitle>Upload Your Materials</CardTitle>
          <CardDescription>
            Upload your resume and paste the job description you're targeting
          </CardDescription>
          <div className="mt-4 p-4 bg-primary-500/10 border border-primary-500/20 rounded-lg">
            <p className="text-sm text-primary-200">
              <span className="font-semibold text-primary-400">Tip:</span> Refine analyzes your content against job descriptions to suggest impactful, honest improvements to best showcase your qualifications.
            </p>
          </div>
        </CardHeader>
        
        <CardContent className="space-y-8">
          <div className="space-y-4">
            <div className="flex p-1 bg-neutral-800 border border-white/10 rounded-lg w-fit">
              <button
                type="button"
                onClick={() => setUploadType('text')}
                className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  uploadType === 'text'
                    ? 'bg-neutral-700 text-white shadow-sm'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                <ClipboardCheck className="h-4 w-4 mr-2" />
                Paste LaTeX Code
              </button>
              <button
                type="button"
                onClick={() => setUploadType('file')}
                className={`flex items-center px-4 py-2 rounded-md text-sm font-medium transition-all ${
                  uploadType === 'file'
                    ? 'bg-neutral-700 text-white shadow-sm'
                    : 'text-neutral-400 hover:text-white'
                }`}
              >
                <Upload className="h-4 w-4 mr-2" />
                Upload .tex File
              </button>
            </div>
            
            {uploadType === 'file' ? (
              <FileUpload
                label="Your Resume (.tex)"
                hint="Upload your current resume in LaTeX (.tex) format"
                accept=".tex"
                onFileSelect={handleResumeFileSelect}
                error={errors.resume}
              />
            ) : (
              <TextArea
                label="Your Resume (LaTeX code)"
                placeholder="Paste your LaTeX resume code here..."
                value={resumeText}
                onChange={(e) => setResumeText(e.target.value)}
                error={errors.resume}
                className="min-h-[200px] font-mono"
              />
            )}
          </div>
          
          <TextArea
            label="Job Description"
            placeholder="Paste the full job description here..."
            value={jobDescription}
            onChange={(e) => setJobDescription(e.target.value)}
            error={errors.jobDescription}
            className="min-h-[200px]"
          />
        </CardContent>
        
        <CardFooter className="flex justify-end">
          <Button
            onClick={handleSubmit}
            icon={<ArrowRight className="h-4 w-4" />}
            iconPosition="right"
          >
            Continue
          </Button>
        </CardFooter>
      </Card>
    </div>
  );
};

export default UploadStep;
