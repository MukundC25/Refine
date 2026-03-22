import React from 'react';
import HeroSection from './HeroSection';
import HowItWorksSection from './HowItWorksSection';
import FeaturesSection from './FeaturesSection';
import DemoSection from './DemoSection';
import FAQSection from './FAQSection';
import CTASection from './CTASection';

interface LandingPageProps {
  onStart?: () => void;
}

const LandingPage: React.FC<LandingPageProps> = ({ onStart }) => {
  return (
    <main className="bg-neutral-charcoal min-h-screen">
      <HeroSection onStart={onStart} />
      
      <div id="how-it-works">
        <HowItWorksSection />
      </div>
      
      <div id="features">
        <FeaturesSection />
      </div>
      
      <DemoSection />
      
      <div id="faq">
        <FAQSection />
      </div>
      
      <CTASection onStart={onStart} />
    </main>
  );
};

export default LandingPage;
