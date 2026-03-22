import React from 'react';
import Section from '../ui/Section';
import { motion } from 'framer-motion';
import { Card } from '../ui/Card';

const DemoSection = () => {
  return (
    <Section className="bg-neutral-charcoal">
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center">
        <motion.div
          initial={{ opacity: 0, x: -20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
        >
          <h2 className="text-3xl md:text-4xl font-display font-bold mb-6">
            See the Difference <span className="text-primary-400">Refine</span> Makes
          </h2>
          <p className="text-lg text-neutral-silver/80 mb-8 leading-relaxed">
            Our AI doesn't just fix typos. It completely restructures your bullet points to focus on impact, quantifies your achievements, and aligns your keywords with the job description.
          </p>
          
          <div className="space-y-6">
            <div className="border-l-2 border-white/10 pl-6">
              <h4 className="text-lg font-bold text-white mb-2">Before Optimization</h4>
              <p className="text-neutral-400 italic">"Responsible for managing team projects and ensuring deadlines were met."</p>
            </div>
            <div className="border-l-2 border-secondary-mint pl-6">
              <h4 className="text-lg font-bold text-secondary-mint mb-2">After Optimization</h4>
              <p className="text-white font-medium">"Led a cross-functional team of 8 engineers to deliver 3 high-priority projects under budget, reducing time-to-market by 20%."</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, x: 20 }}
          whileInView={{ opacity: 1, x: 0 }}
          viewport={{ once: true }}
          className="relative"
        >
          <Card variant="glass-dark" className="p-8 border border-white/10">
            <div className="flex items-center justify-between mb-8">
              <h3 className="text-xl font-bold">Refine Score</h3>
              <div className="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-sm font-bold">
                Top 5% Candidate
              </div>
            </div>

            {/* Animated Bars */}
            <div className="space-y-6">
              {[
                { label: "Impact", score: 95, color: "bg-primary-500" },
                { label: "Relevance", score: 92, color: "bg-secondary-purple" },
                { label: "Skills Match", score: 88, color: "bg-secondary-mint" },
                { label: "Brevity", score: 90, color: "bg-blue-400" },
              ].map((item, i) => (
                <div key={i}>
                  <div className="flex justify-between mb-2 text-sm">
                    <span className="text-neutral-300">{item.label}</span>
                    <span className="text-white font-bold">{item.score}%</span>
                  </div>
                  <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                    <motion.div 
                      initial={{ width: 0 }}
                      whileInView={{ width: `${item.score}%` }}
                      viewport={{ once: true }}
                      transition={{ duration: 1.5, delay: 0.2 + (i * 0.1) }}
                      className={`h-full rounded-full ${item.color}`}
                    />
                  </div>
                </div>
              ))}
            </div>
            
            <div className="mt-8 pt-6 border-t border-white/5 text-center">
               <p className="text-sm text-neutral-400">Analysis based on 50+ hiring parameters</p>
            </div>
          </Card>
          
          {/* Decorative Elements */}
          <div className="absolute -top-10 -right-10 w-32 h-32 bg-primary-500/20 rounded-full blur-[50px] -z-10" />
          <div className="absolute -bottom-10 -left-10 w-32 h-32 bg-secondary-mint/20 rounded-full blur-[50px] -z-10" />
        </motion.div>
      </div>
    </Section>
  );
};

export default DemoSection;
