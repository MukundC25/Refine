import React, { useState, useEffect } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../ui/Card';
import Button from '../ui/Button';
import TextArea from '../ui/TextArea';
import { X, User as UserIcon } from 'lucide-react';
import { User } from '../../lib/types';

interface ProfileModalProps {
  isOpen: boolean;
  onClose: () => void;
  user: User;
  onUpdate: (updatedUser: User) => void;
}

const ProfileModal: React.FC<ProfileModalProps> = ({ isOpen, onClose, user, onUpdate }) => {
  const [fullName, setFullName] = useState(user.full_name || '');
  const [resumeLatex, setResumeLatex] = useState(user.resume_latex || '');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (isOpen) {
        setFullName(user.full_name || '');
        setResumeLatex(user.resume_latex || '');
        setError('');
        setSuccess('');
    }
  }, [isOpen, user]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setSuccess('');
    setLoading(true);

    try {
      const token = localStorage.getItem('refine_token');
      const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${API_BASE}/users/me`, {
        method: 'PUT',
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ full_name: fullName, resume_latex: resumeLatex }),
      });

      if (!response.ok) {
        throw new Error('Failed to update profile');
      }

      const updatedUser = await response.json();
      onUpdate(updatedUser);
      setSuccess('Profile updated successfully!');
      setTimeout(() => {
          onClose();
      }, 1500);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fade-in">
      <Card className="max-w-2xl w-full bg-neutral-900 border-primary-500/30 shadow-2xl relative max-h-[90vh] flex flex-col">
        <button 
            onClick={onClose}
            className="absolute top-4 right-4 text-neutral-400 hover:text-white transition-colors"
        >
            <X size={20} />
        </button>
        
        <CardHeader>
          <CardTitle className="text-center text-white text-2xl font-bold">
            Your Profile
          </CardTitle>
        </CardHeader>
        
        <CardContent className="space-y-6 overflow-y-auto flex-1">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-md text-red-400 text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="p-3 bg-green-500/10 border border-green-500/20 rounded-md text-green-400 text-sm">
              {success}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
                <label className="text-sm font-medium text-neutral-300">Full Name</label>
                <div className="relative">
                    <UserIcon className="absolute left-3 top-3 h-4 w-4 text-neutral-500" />
                    <input
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        className="w-full bg-neutral-800 border border-white/10 rounded-lg py-2.5 pl-10 pr-4 text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all"
                        placeholder="John Doe"
                        required
                    />
                </div>
            </div>

            <div className="space-y-2">
                <label className="text-sm font-medium text-neutral-300">Saved Resume (LaTeX)</label>
                <TextArea
                    value={resumeLatex}
                    onChange={(e) => setResumeLatex(e.target.value)}
                    className="min-h-[300px] font-mono text-xs"
                    placeholder="\documentclass{article}..."
                />
                <p className="text-xs text-neutral-500">
                    This resume content will be automatically loaded when you start a new optimization.
                </p>
            </div>

            <Button fullWidth type="submit" disabled={loading} glow>
                {loading ? 'Saving...' : 'Save Changes'}
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};

export default ProfileModal;
