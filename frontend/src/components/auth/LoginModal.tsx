import React, { useState } from 'react';
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from '../ui/Card';
import Button from '../ui/Button';
import { X, Mail, Lock, User as UserIcon } from 'lucide-react';

interface LoginModalProps {
  isOpen: boolean;
  onClose: () => void;
  onLoginSuccess: (token: string, user: any) => void;
}

const LoginModal: React.FC<LoginModalProps> = ({ isOpen, onClose, onLoginSuccess }) => {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setLoading(true);

    const endpoint = isLogin ? '/login' : '/signup';
    const body = isLogin 
      ? new URLSearchParams({ username: email, password }) 
      : JSON.stringify({ email, password, full_name: fullName });

    const headers: HeadersInit = isLogin 
        ? { 'Content-Type': 'application/x-www-form-urlencoded' }
        : { 'Content-Type': 'application/json' };

    try {
      const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";
      const response = await fetch(`${API_BASE}${endpoint}`, {
        method: 'POST',
        headers,
        body,
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Authentication failed');
      }

      const data = await response.json();
      
      if (isLogin) {
          onLoginSuccess(data.access_token, { email }); // Ideally fetch user profile after login
      } else {
          // Auto login after signup or switch to login
          setIsLogin(true);
          setError('Account created! Please log in.');
          setLoading(false);
          return; 
      }
      
      onClose();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4 animate-fade-in">
      <Card className="max-w-md w-full bg-neutral-900 border-primary-500/30 shadow-2xl relative">
        <button 
            onClick={onClose}
            className="absolute top-4 right-4 text-neutral-400 hover:text-white transition-colors"
        >
            <X size={20} />
        </button>
        
        <CardHeader>
          <CardTitle className="text-center text-white text-2xl font-bold">
            {isLogin ? 'Welcome Back' : 'Create Account'}
          </CardTitle>
        </CardHeader>
        
        <CardContent className="space-y-6">
          {error && (
            <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-md text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            {!isLogin && (
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
            )}
            
            <div className="space-y-2">
                <label className="text-sm font-medium text-neutral-300">Email</label>
                <div className="relative">
                    <Mail className="absolute left-3 top-3 h-4 w-4 text-neutral-500" />
                    <input
                        type="email"
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        className="w-full bg-neutral-800 border border-white/10 rounded-lg py-2.5 pl-10 pr-4 text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all"
                        placeholder="you@example.com"
                        required
                    />
                </div>
            </div>

            <div className="space-y-2">
                <label className="text-sm font-medium text-neutral-300">Password</label>
                <div className="relative">
                    <Lock className="absolute left-3 top-3 h-4 w-4 text-neutral-500" />
                    <input
                        type="password"
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        className="w-full bg-neutral-800 border border-white/10 rounded-lg py-2.5 pl-10 pr-4 text-white focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none transition-all"
                        placeholder="••••••••"
                        required
                        minLength={6}
                    />
                </div>
            </div>

            <Button fullWidth type="submit" disabled={loading} glow>
                {loading ? 'Processing...' : (isLogin ? 'Sign In' : 'Sign Up')}
            </Button>
          </form>
        </CardContent>
        
        <CardFooter className="justify-center border-t border-white/5 pt-4">
            <p className="text-neutral-400 text-sm">
                {isLogin ? "Don't have an account? " : "Already have an account? "}
                <button 
                    onClick={() => setIsLogin(!isLogin)}
                    className="text-primary-400 hover:text-primary-300 font-medium transition-colors"
                >
                    {isLogin ? 'Sign up' : 'Log in'}
                </button>
            </p>
        </CardFooter>
      </Card>
    </div>
  );
};

export default LoginModal;
