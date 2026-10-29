import React from 'react';

interface NotFoundViewProps {
  onGoHome: () => void;
}

export const NotFoundView: React.FC<NotFoundViewProps> = ({ onGoHome }) => {
  return (
    <div className="min-h-[60vh] flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-10 max-w-lg w-full text-center space-y-6 shadow-2xl">
        <div className="text-6xl mx-auto">
          🔍
        </div>

        <div>
          <h2 className="text-5xl font-extrabold text-cyan-400 font-mono tracking-tight">404</h2>
          <h3 className="text-xl font-bold text-white mt-2">Page Not Found</h3>
          <p className="text-xs text-slate-400 mt-2 leading-relaxed">
            The analytical resource or gateway endpoint you are looking for does not exist or has been moved.
          </p>
        </div>

        <button
          onClick={onGoHome}
          className="py-2.5 px-6 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-semibold text-white text-xs transition shadow-md shadow-cyan-950"
        >
          ← Go Back Home
        </button>
      </div>
    </div>
  );
};

