import React, { useState, useRef } from 'react';
import { cn } from '../../lib/utils';
import { Upload, File, X } from 'lucide-react';

interface FileUploadProps {
  accept?: string;
  maxSize?: number; // in bytes
  onFileSelect: (file: File) => void;
  label?: string;
  hint?: string;
  error?: string;
  className?: string;
}

const FileUpload: React.FC<FileUploadProps> = ({
  accept = '.tex',
  maxSize = 5 * 1024 * 1024, // 5MB default
  onFileSelect,
  label = 'Upload a file',
  hint,
  error,
  className,
}) => {
  const [dragActive, setDragActive] = useState(false);
  const [fileError, setFileError] = useState<string | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateFile = (file: File): boolean => {
    // Check file type/extension for .tex
    if (accept && !file.name.toLowerCase().endsWith('.tex') && file.type !== 'text/x-tex') {
      setFileError('Please upload a LaTeX (.tex) file.');
      return false;
    }
    // Check file size
    if (file.size > maxSize) {
      setFileError(`File size must be less than ${maxSize / (1024 * 1024)}MB.`);
      return false;
    }
    setFileError(null);
    return true;
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
        onFileSelect(file);
      }
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    e.preventDefault();
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      if (validateFile(file)) {
        setSelectedFile(file);
        onFileSelect(file);
      }
    }
  };

  const handleButtonClick = () => {
    inputRef.current?.click();
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (inputRef.current) {
      inputRef.current.value = '';
    }
  };

  return (
    <div className={cn('w-full', className)}>
      {label && (
        <p className="block text-sm font-medium text-neutral-300 mb-1.5">{label}</p>
      )}
      
      <div
        className={cn(
          'flex flex-col items-center justify-center w-full border-2 border-dashed rounded-xl p-8 transition-all cursor-pointer',
          dragActive 
            ? 'border-primary-500 bg-primary-500/10' 
            : 'border-white/10 hover:border-primary-400/50 hover:bg-white/5',
          selectedFile ? 'bg-white/5 border-primary-500/50' : 'bg-transparent',
          (error || fileError) && 'border-red-500/50 bg-red-500/5'
        )}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        onClick={handleButtonClick}
      >
        <input
          ref={inputRef}
          type="file"
          className="hidden"
          accept={accept}
          onChange={handleChange}
        />
        
        {selectedFile ? (
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center">
              <div className="p-3 rounded-lg bg-neutral-800 border border-white/10 mr-4">
                <File className="h-6 w-6 text-primary-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-white">{selectedFile.name}</p>
                <p className="text-xs text-neutral-400">{(selectedFile.size / 1024).toFixed(1)} KB</p>
              </div>
            </div>
            <button
              type="button"
              className="text-neutral-400 hover:text-white p-2 rounded-full hover:bg-white/10 transition-colors"
              onClick={(e) => {
                e.stopPropagation();
                handleRemoveFile();
              }}
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        ) : (
          <>
            <div className="p-4 rounded-full bg-white/5 mb-4">
              <Upload className="h-8 w-8 text-neutral-400" />
            </div>
            <p className="text-sm text-neutral-300 font-medium">
              Drag & drop your .tex file here or <span className="text-primary-400 hover:underline">browse</span>
            </p>
            <p className="mt-2 text-xs text-neutral-500">
              LaTeX (.tex) files only, max {maxSize / (1024 * 1024)}MB
            </p>
          </>
        )}
      </div>
      
      {(hint || error || fileError) && (
        <p className={cn(
          'mt-2 text-sm',
          (error || fileError) ? 'text-red-400' : 'text-neutral-500'
        )}>
          {error || fileError || hint}
        </p>
      )}
    </div>
  );
};

export default FileUpload;
