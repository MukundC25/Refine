import React, { useState } from 'react';

export const ReasoningCell: React.FC<{ reasoning: string }> = ({ reasoning }) => {
  const [isHovered, setIsHovered] = useState(false);

  return (
    <div 
      className="relative cursor-help"
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      <div className="text-zinc-300 line-clamp-2 text-sm leading-tight">
        {reasoning}
      </div>
      
      {isHovered && (
        <div className="absolute z-50 left-0 top-full mt-1 w-64 p-3 bg-zinc-800 border border-zinc-700 rounded-lg shadow-xl text-xs text-zinc-200 break-words pointer-events-none">
          {reasoning}
        </div>
      )}
    </div>
  );
};
