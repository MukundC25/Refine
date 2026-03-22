import React from 'react';
import Section from '../ui/Section';
import Button from '../ui/Button';
import { motion } from 'framer-motion';
import { FileText, ArrowRight, CheckCircle, Sparkles } from 'lucide-react';

interface HeroSectionProps {
  onStart?: () => void;
}

const HeroSection: React.FC<HeroSectionProps> = ({ onStart }) => {
  return (
    <Section className="pt-32 pb-20 md:pt-40 md:pb-32 overflow-hidden">
      {/* Background Elements */}
      <div className="absolute top-0 left-0 w-full h-full overflow-hidden -z-10 pointer-events-none">
        <div className="absolute top-[-10%] right-[-5%] w-[500px] h-[500px] bg-primary-500/20 rounded-full blur-[100px] animate-pulse" />
        <div className="absolute bottom-[-10%] left-[-10%] w-[600px] h-[600px] bg-secondary-purple/20 rounded-full blur-[120px]" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-12 items-center">
        {/* Text Content */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="relative z-10"
        >
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-sm text-secondary-mint mb-6">
            <Sparkles size={14} />
            <span>AI-Powered Resume Optimization</span>
          </div>
          
          <h1 className="text-4xl md:text-5xl lg:text-6xl font-display font-bold leading-tight mb-6">
            Transform Your Resume Into a <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-secondary-purple">Job-Ready Powerhouse.</span>
          </h1>
          
          <p className="text-lg md:text-xl text-neutral-silver/80 mb-8 max-w-xl leading-relaxed">
            Refine uses AI hiring-manager intelligence to evaluate, score, and rewrite your resume for any job description — automatically, in perfect LaTeX.
          </p>
          
          <div className="flex flex-col sm:flex-row gap-4">
            <Button variant="primary" size="lg" glow icon={<Sparkles size={18} />} iconPosition="right" onClick={onStart}>
              Optimize My Resume
            </Button>
            <Button variant="outline" size="lg" icon={<ArrowRight size={18} />} iconPosition="right" onClick={() => document.getElementById('how-it-works')?.scrollIntoView({ behavior: 'smooth' })}>
              See How It Works
            </Button>
          </div>

          <div className="mt-8 flex items-center gap-6 text-sm text-neutral-silver/60">
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-secondary-mint" />
              <span>ATS Friendly</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-secondary-mint" />
              <span>LaTeX Output</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle size={16} className="text-secondary-mint" />
              <span>Instant Scoring</span>
            </div>
          </div>
        </motion.div>

        {/* 3D Visual Element */}
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, delay: 0.2 }}
          className="relative perspective-1000 h-[500px] w-full flex items-center justify-center"
        >
          {/* Floating Document Container */}
          <motion.div 
            animate={{ 
              y: [-20, 20, -20],
              rotateX: [5, -5, 5],
              rotateY: [-5, 5, -5]
            }}
            transition={{ 
              duration: 6,
              repeat: Infinity,
              ease: "easeInOut"
            }}
            className="relative preserve-3d w-[320px] h-[460px] bg-neutral-900 border border-white/10 rounded-xl shadow-2xl"
            style={{
              transformStyle: 'preserve-3d',
              transform: 'rotateX(10deg) rotateY(-10deg)'
            }}
          >
            {/* Document Header */}
            <div className="absolute top-0 w-full p-6 border-b border-white/5 bg-white/5 rounded-t-xl">
              <div className="flex gap-2">
                <div className="w-3 h-3 rounded-full bg-red-500/50" />
                <div className="w-3 h-3 rounded-full bg-yellow-500/50" />
                <div className="w-3 h-3 rounded-full bg-green-500/50" />
              </div>
            </div>

            {/* Resume Content Simulation */}
            <div className="p-8 pt-20 space-y-4 opacity-80">
              {/* Header */}
              <div className="flex justify-between items-start mb-8">
                <div className="space-y-2">
                  <div className="h-6 w-32 bg-white/20 rounded" />
                  <div className="h-3 w-48 bg-white/10 rounded" />
                </div>
                <div className="h-12 w-12 rounded-full bg-gradient-to-tr from-primary-500 to-secondary-purple" />
              </div>

              {/* Sections */}
              {[1, 2, 3].map((i) => (
                <div key={i} className="space-y-2">
                  <div className="h-4 w-24 bg-primary-500/30 rounded mb-3" />
                  <div className="h-2 w-full bg-white/10 rounded" />
                  <div className="h-2 w-5/6 bg-white/10 rounded" />
                  <div className="h-2 w-4/6 bg-white/10 rounded" />
                </div>
              ))}
            </div>

            {/* Floating Badge - Score */}
            <motion.div 
              animate={{ y: [5, -5, 5] }}
              transition={{ duration: 4, repeat: Infinity, ease: "easeInOut", delay: 1 }}
              className="absolute -right-8 top-20 bg-neutral-800/90 backdrop-blur-md border border-white/10 p-4 rounded-lg shadow-xl"
            >
              <div className="flex items-center gap-3">
                <div className="radial-progress text-secondary-mint text-xs font-bold" style={{"--value":92, "--size": "2.5rem"} as any}>92</div>
                <div>
                  <div className="text-xs text-neutral-400">Resume Score</div>
                  <div className="text-sm font-bold text-white">Excellent</div>
                </div>
              </div>
            </motion.div>

            {/* Floating Badge - AI Analysis */}
            <motion.div 
              animate={{ y: [-5, 5, -5] }}
              transition={{ duration: 5, repeat: Infinity, ease: "easeInOut", delay: 0.5 }}
              className="absolute -left-12 bottom-32 bg-neutral-800/90 backdrop-blur-md border border-white/10 p-4 rounded-lg shadow-xl max-w-[180px]"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 bg-primary-500/20 rounded-md text-primary-400">
                  <Sparkles size={16} />
                </div>
                <div>
                  <div className="text-xs text-neutral-400 mb-1">AI Suggestion</div>
                  <div className="text-xs text-white leading-tight">Quantify your impact with metrics in this section.</div>
                </div>
              </div>
            </motion.div>
            
            {/* Glow Effect behind document */}
            <div className="absolute inset-0 bg-primary-500/20 blur-3xl -z-10 transform translate-z-[-50px]" />
          </motion.div>
        </motion.div>
      </div>

      {/* Scroll Indicator */}
      <motion.div 
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ delay: 1, duration: 1 }}
        className="absolute bottom-8 left-1/2 transform -translate-x-1/2 flex flex-col items-center gap-2"
      >
        <span className="text-xs text-neutral-500 uppercase tracking-widest">Scroll</span>
        <motion.div
          animate={{ y: [0, 10, 0] }}
          transition={{ duration: 2, repeat: Infinity }}
        >
          <div className="w-1 h-12 rounded-full bg-gradient-to-b from-primary-500/50 to-transparent" />
        </motion.div>
      </motion.div>
    </Section>
  );
};

export default HeroSection;
