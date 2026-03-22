import React from 'react';
import Section from '../ui/Section';
import { Card, CardContent } from '../ui/Card';
import { motion } from 'framer-motion';
import { 
  UserCheck, 
  AlertCircle, 
  FileCode, 
  BarChart2, 
  Zap, 
  Download 
} from 'lucide-react';

const features = [
  {
    title: 'AI Hiring Manager Analysis',
    description: 'Benchmarks your experience, skills, and projects against strict hiring criteria.',
    icon: <UserCheck className="text-primary-400" size={24} />,
    gradient: 'from-primary-500/20 to-transparent'
  },
  {
    title: 'Gap Detection',
    description: 'Identifies missing competencies, keywords, and ATS weaknesses in real-time.',
    icon: <AlertCircle className="text-secondary-purple" size={24} />,
    gradient: 'from-secondary-purple/20 to-transparent'
  },
  {
    title: 'LaTeX-Preserving Rewrite',
    description: 'Completes rewrites while maintaining your original LaTeX structure and formatting.',
    icon: <FileCode className="text-secondary-mint" size={24} />,
    gradient: 'from-secondary-mint/20 to-transparent'
  },
  {
    title: 'Category-Based Scoring',
    description: 'Detailed percent scores for Experience, Skills, Projects, Relevance, and Impact.',
    icon: <BarChart2 className="text-blue-400" size={24} />,
    gradient: 'from-blue-500/20 to-transparent'
  },
  {
    title: 'Instant Optimization',
    description: 'Tailors your resume content to specific job descriptions in seconds.',
    icon: <Zap className="text-yellow-400" size={24} />,
    gradient: 'from-yellow-500/20 to-transparent'
  },
  {
    title: 'Download-Ready Output',
    description: 'Get a clean, professional, and compilable LaTeX file ready for submission.',
    icon: <Download className="text-pink-400" size={24} />,
    gradient: 'from-pink-500/20 to-transparent'
  }
];

const FeaturesSection = () => {
  return (
    <Section className="bg-neutral-900 border-y border-white/5">
      <div className="text-center mb-16">
        <motion.h2 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          className="text-3xl md:text-4xl font-display font-bold mb-4"
        >
          Powerful Features
        </motion.h2>
        <p className="text-neutral-silver/60 max-w-2xl mx-auto text-lg">
          Everything you need to perfect your resume and beat the ATS.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {features.map((feature, index) => (
          <motion.div
            key={index}
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ delay: index * 0.1 }}
          >
            <Card 
              variant="glass" 
              hoverEffect 
              className="h-full border-white/5 bg-white/5 hover:bg-white/10 transition-colors"
            >
              <CardContent className="p-8 relative overflow-hidden h-full">
                {/* Gradient Background */}
                <div className={`absolute top-0 left-0 w-full h-full bg-gradient-to-br ${feature.gradient} opacity-20`} />
                
                <div className="relative z-10">
                  <div className="w-12 h-12 rounded-lg bg-neutral-900 border border-white/10 flex items-center justify-center mb-6">
                    {feature.icon}
                  </div>
                  
                  <h3 className="text-xl font-bold text-white mb-3">
                    {feature.title}
                  </h3>
                  
                  <p className="text-neutral-silver/70 leading-relaxed">
                    {feature.description}
                  </p>
                </div>
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </div>
    </Section>
  );
};

export default FeaturesSection;
