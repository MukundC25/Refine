import React from 'react';
import { FileText, Twitter, Linkedin, Github } from 'lucide-react';

interface FooterProps {
  onLogoClick?: () => void;
}

const Footer: React.FC<FooterProps> = ({ onLogoClick }) => {
  return (
    <footer className="bg-neutral-900 border-t border-white/5 py-8">
      <div className="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-4">
        <button 
          onClick={onLogoClick}
          className="flex items-center space-x-2 hover:opacity-80 transition-opacity cursor-pointer"
        >
          <div className="bg-gradient-to-br from-primary-500 to-primary-700 p-1.5 rounded-lg">
            <FileText className="h-4 w-4 text-white" />
          </div>
          <span className="text-lg font-display font-bold text-white">Refine</span>
        </button>
        
        <p className="text-sm text-neutral-600">
        </p>
        
        <div className="flex space-x-4">
          <a href="https://github.com/MukundC25/Refine" target="_blank" rel="noopener noreferrer" className="text-neutral-500 hover:text-white transition-colors">
            <Github size={20} />
          </a>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
