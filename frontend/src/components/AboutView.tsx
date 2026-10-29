import React from 'react';

export const AboutView: React.FC = () => {
  return (
    <div className="max-w-4xl mx-auto space-y-8 animate-in fade-in duration-200">
      {/* Brand Hero */}
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-8 text-center space-y-4 shadow-xl">
        <div className="w-16 h-16 rounded-2xl bg-cyan-950/80 border border-cyan-500/50 flex items-center justify-center text-3xl mx-auto shadow-lg shadow-cyan-950">
          🛡️
        </div>
        <div>
          <h2 className="text-2xl font-extrabold text-white tracking-tight">SentinelVault</h2>
          <p className="text-sm font-semibold text-cyan-400 mt-1 uppercase tracking-wider">
            Analyze Data. Don't Expose It.
          </p>
        </div>
        <p className="text-xs text-slate-300 max-w-2xl mx-auto leading-relaxed">
          SentinelVault is a zero-trust, privacy-preserving analytics gateway that enables authorized analysts to obtain 
          useful aggregate insights from sensitive healthcare and financial datasets without revealing raw individual records.
        </p>
        <div className="flex flex-wrap justify-center gap-2 pt-2 text-xs font-mono">
          <span className="px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-slate-400">Team: HOTFIX (UG 59)</span>
          <span className="px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-cyan-400">Track 4: Privacy by Design</span>
          <span className="px-3 py-1 rounded-full bg-slate-950 border border-slate-800 text-emerald-400">Differential Privacy MVP</span>
        </div>
      </div>

      {/* 3 Core Pillars matching Image 15 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-3">
          <div className="text-2xl">🔒</div>
          <h3 className="text-base font-bold text-white">Privacy Preserving</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Laplace mechanism via IBM diffprivlib with bounded sensitivity (Δf = 1.0) and micro-epsilon integer budget ledger accounting.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-3">
          <div className="text-2xl">🛡️</div>
          <h3 className="text-base font-bold text-white">Secure & Compliant</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Zero-trust PBKDF2-HMAC-SHA256 authentication, 5-attempt rate-limit lockout, and fail-closed allowlist query validation.
          </p>
        </div>

        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 space-y-3">
          <div className="text-2xl">📜</div>
          <h3 className="text-base font-bold text-white">Audit Ready</h3>
          <p className="text-xs text-slate-400 leading-relaxed">
            Self-contained cryptographic Privacy Receipts signed with Ed25519 digital signatures and SHA-256 hash-chained tamper detection.
          </p>
        </div>
      </div>

      {/* Honest Compliance Notice */}
      <div className="bg-slate-900/60 border border-amber-800/40 rounded-xl p-5 space-y-2 text-xs">
        <div className="flex items-center gap-2 text-amber-400 font-bold">
          <span>⚠️</span>
          <span>Official Track 4 Competition Disclosure</span>
        </div>
        <p className="text-slate-400 leading-relaxed">
          Demonstration accounting is active using exact micro-epsilon integer calculations. Official competition specification conformance 
          and synthetic adversary benchmarks remain unverified pending integration of the official Track 4 evaluation harness.
        </p>
      </div>
    </div>
  );
};

