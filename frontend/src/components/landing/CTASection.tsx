import React from 'react';
import Section from '../ui/Section';
import Button from '../ui/Button';
import { motion } from 'framer-motion';
import { Github, Globe, Sparkles } from 'lucide-react';

interface CTASectionProps {
  onStart?: () => void;
}

const CTASection: React.FC<CTASectionProps> = ({ onStart }) => {
  return (
    <Section className="relative py-24 md:py-32 overflow-hidden">
      {/* Background Gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-primary-900 to-secondary-purple/30" />
      
      {/* Animated Glows */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-primary-500/30 rounded-full blur-[120px] animate-pulse" />
      <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-secondary-purple/20 rounded-full blur-[120px]" />

      <div className="relative z-10 text-center max-w-4xl mx-auto">
        <motion.h2 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-4xl md:text-5xl lg:text-6xl font-display font-bold mb-6 text-white"
        >
          Ready to Land More Interviews?
        </motion.h2>
        
        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ delay: 0.1 }}
          className="text-xl text-neutral-200 mb-10 max-w-2xl mx-auto"
        >
          This application is currently restricted. To use it, you can clone the repository and set up your own Gemini API key, or contact the developer for access.
        </motion.p>
        
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          whileInView={{ opacity: 1, scale: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.2 }}
          className="flex flex-col sm:flex-row gap-4 justify-center"
        >
          <a href="https://github.com/MukundC25/Refine" target="_blank" rel="noopener noreferrer">
            <Button size="lg" glow icon={<Github size={20} />} iconPosition="left">
              Clone on GitHub
            </Button>
          </a>
          <a href="https://mukund-ashy.vercel.app/" target="_blank" rel="noopener noreferrer">
            <Button variant="outline" size="lg" className="bg-white/5 backdrop-blur-sm border-white/20 hover:bg-white/10" icon={<Globe size={20} />} iconPosition="left">
              Contact Developer
            </Button>
          </a>
        </motion.div>

        <motion.div 
          initial={{ opacity: 0 }}
          whileInView={{ opacity: 1 }}
          viewport={{ once: true }}
          transition={{ delay: 0.4 }}
          className="mt-12 text-sm text-neutral-400"
        >
          Self-host with your own API Key • Request Access
        </motion.div>
      </div>
    </Section>
  );
};

export default CTASection;
