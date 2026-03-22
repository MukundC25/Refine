import React, { useState } from 'react';
import Section from '../ui/Section';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Minus } from 'lucide-react';

const faqs = [
  {
    question: 'How does the AI scoring work?',
    answer: 'Our AI analyzes your resume against thousands of successful resumes and specific job descriptions. It evaluates key metrics like impact quantification, keyword relevance, formatting, and brevity to generate a comprehensive score.',
  },
  {
    question: 'Will my LaTeX formatting be preserved?',
    answer: 'Yes! Refine is built specifically for LaTeX users. Our engine understands TeX syntax and ensures that your structure, styling, and commands remain intact while the content is optimized.',
  },
  {
    question: 'Is my data secure?',
    answer: 'Absolutely. We do not store your resume content or personal data after the session ends. Your uploaded files are processed in memory and discarded immediately after optimization.',
  },
  {
    question: 'Can I optimize for multiple job descriptions?',
    answer: 'Yes. With our Pro and Premium plans, you can run unlimited optimizations, tailoring your resume for every single job application to maximize your chances.',
  },
];

const FAQItem = ({ question, answer, isOpen, onClick }: { question: string, answer: string, isOpen: boolean, onClick: () => void }) => {
  return (
    <motion.div 
      initial={false}
      className={`border border-white/10 rounded-xl overflow-hidden transition-colors ${isOpen ? 'bg-white/5' : 'hover:bg-white/5'}`}
    >
      <button
        onClick={onClick}
        className="w-full px-6 py-5 flex items-center justify-between text-left focus:outline-none"
      >
        <span className="font-medium text-lg text-white">{question}</span>
        <div className={`p-1 rounded-full ${isOpen ? 'bg-primary-500/20 text-primary-400' : 'bg-white/10 text-neutral-400'}`}>
          {isOpen ? <Minus size={18} /> : <Plus size={18} />}
        </div>
      </button>
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
          >
            <div className="px-6 pb-6 pt-0 text-neutral-silver/70 leading-relaxed">
              {answer}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

const FAQSection = () => {
  const [openIndex, setOpenIndex] = useState<number | null>(0);

  return (
    <Section className="bg-neutral-charcoal">
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-12">
        <div className="lg:col-span-4">
          <motion.h2 
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            className="text-3xl md:text-4xl font-display font-bold mb-4"
          >
            Frequently Asked Questions
          </motion.h2>
          <p className="text-neutral-silver/60 text-lg mb-8">
            Everything you need to know about optimizing your resume with Refine.
          </p>
          <div className="hidden lg:block p-6 rounded-2xl bg-gradient-to-br from-primary-900/30 to-secondary-purple/10 border border-white/5">
            <h4 className="text-white font-bold mb-2">Still have questions?</h4>
            <p className="text-sm text-neutral-400 mb-4">We're here to help you land your dream job.</p>
            <button className="text-primary-400 text-sm font-medium hover:text-primary-300 transition-colors">
              Contact Support &rarr;
            </button>
          </div>
        </div>

        <div className="lg:col-span-8 space-y-4">
          {faqs.map((faq, index) => (
            <FAQItem
              key={index}
              question={faq.question}
              answer={faq.answer}
              isOpen={openIndex === index}
              onClick={() => setOpenIndex(openIndex === index ? null : index)}
            />
          ))}
        </div>
      </div>
    </Section>
  );
};

export default FAQSection;
