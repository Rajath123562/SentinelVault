import React from 'react';

interface LoadingModalProps {
  isOpen: boolean;
  message?: string;
  subMessage?: string;
}

export const LoadingModal: React.FC<LoadingModalProps> = ({
  isOpen,
  message = 'Processing your query...',
  subMessage = 'Applying differential privacy and checking privacy budget. This may take a few seconds.',
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-700/80 rounded-2xl p-8 max-w-md w-full shadow-2xl text-center space-y-5 animate-in fade-in zoom-in-95 duration-200">
        <div className="relative w-16 h-16 mx-auto flex items-center justify-center">
          <div className="w-16 h-16 rounded-full border-4 border-slate-800 border-t-cyan-500 animate-spin"></div>
          <span className="absolute text-xl">🛡️</span>
        </div>
        <div>
          <h3 className="text-lg font-bold text-white tracking-tight">{message}</h3>
          <p className="text-xs text-slate-400 mt-2 leading-relaxed">{subMessage}</p>
        </div>
        <div className="inline-block px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-[11px] font-mono text-cyan-400">
          IBM diffprivlib • Laplace Mechanism
        </div>
      </div>
    </div>
  );
};

