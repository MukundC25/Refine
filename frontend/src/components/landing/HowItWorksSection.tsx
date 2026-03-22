import React from 'react';
import Section from '../ui/Section';
import { motion } from 'framer-motion';
import { Upload, ClipboardList, FileCheck, ArrowRight } from 'lucide-react';

const steps = [
  {
    id: 1,
    title: 'Upload Your Resume',
    description: 'Paste your LaTeX content or upload your existing .tex file to get started.',
    icon: <Upload className="text-primary-400" size={32} />,
    color: 'from-primary-400/20 to-primary-600/5',
  },
  {
    id: 2,
    title: 'Paste Job Description',
    description: 'Our AI evaluates your fit with the lens of a strict hiring manager.',
    icon: <ClipboardList className="text-secondary-purple" size={32} />,
    color: 'from-secondary-purple/20 to-secondary-purple/5',
  },
  {
    id: 3,
    title: 'Get Optimized Resume',
    description: 'Receive a scored evaluation and a rewritten, polished resume tailored for ATS.',
    icon: <FileCheck className="text-secondary-mint" size={32} />,
    color: 'from-secondary-mint/20 to-secondary-mint/5',
  },
];

const HowItWorksSection = () => {
  return (
    <Section className="bg-neutral-charcoal relative">
      <div className="text-center mb-16">
        <motion.span 
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          className="text-secondary-mint font-mono text-sm tracking-wider uppercase mb-4 block"
        >
          Simple Process
        </motion.span>
        <motion.h2 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-3xl md:text-4xl lg:text-5xl font-display font-bold mb-4"
        >
          How Refine Works
        </motion.h2>
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="text-neutral-silver/60 max-w-2xl mx-auto text-lg"
        >
          Three simple steps to transform your resume into an interview magnet.
        </motion.p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
        {/* Connecting Line (Desktop only) */}
        <div className="hidden md:block absolute top-1/2 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-y-1/2 z-0" />

        {steps.map((step, index) => (
          <motion.div
            key={step.id}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.2 }}
            className="relative z-10 group"
          >
            <div className={`bg-neutral-800/50 backdrop-blur-sm border border-white/5 p-8 rounded-2xl h-full transition-all duration-300 hover:-translate-y-2 hover:border-white/20 bg-gradient-to-b ${step.color}`}>
              <div className="mb-6 relative">
                <div className="w-16 h-16 rounded-2xl bg-neutral-900 flex items-center justify-center border border-white/10 shadow-xl group-hover:scale-110 transition-transform duration-300">
                  {step.icon}
                </div>
                <div className="absolute -top-3 -right-3 w-8 h-8 rounded-full bg-neutral-800 border border-white/10 flex items-center justify-center font-mono text-sm text-white font-bold">
                  {step.id}
                </div>
              </div>
              
              <h3 className="text-xl font-bold text-white mb-3 group-hover:text-primary-300 transition-colors">
                {step.title}
              </h3>
              
              <p className="text-neutral-silver/70 leading-relaxed">
                {step.description}
              </p>
            </div>
          </motion.div>
        ))}
      </div>
    </Section>
  );
};

export default HowItWorksSection;
