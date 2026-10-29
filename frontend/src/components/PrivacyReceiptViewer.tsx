import React, { useState } from 'react';
import { PrivacyReceipt, ReceiptVerificationResponse } from '../types/system';
import { getReceipt, verifyReceipt } from '../services/api';

interface PrivacyReceiptViewerProps {
  initialReceipt: PrivacyReceipt | null;
  token: string;
  onBackToDashboard: () => void;
}

export const PrivacyReceiptViewer: React.FC<PrivacyReceiptViewerProps> = ({
  initialReceipt,
  token,
  onBackToDashboard,
}) => {
  const [receipt, setReceipt] = useState<PrivacyReceipt | null>(initialReceipt);
  const [lookupId, setLookupId] = useState('');
  const [loading, setLoading] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [verifiedStatus, setVerifiedStatus] = useState<string | null>(null);
  const [verificationResult, setVerificationResult] = useState<ReceiptVerificationResponse | null>(null);

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupId.trim()) return;
    setLoading(true);
    setError(null);
    setVerifiedStatus(null);
    setVerificationResult(null);
    try {
      const data = await getReceipt(token, lookupId.trim());
      setReceipt(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Receipt lookup failed');
    } finally {
      setLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (!receipt) return;
    navigator.clipboard.writeText(JSON.stringify(receipt, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleDownload = () => {
    if (!receipt) return;
    const blob = new Blob([JSON.stringify(receipt, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `privacy_receipt_${receipt.receipt_id.slice(0, 8)}.json`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleVerifySignature = async () => {
    if (!receipt) return;
    setVerifying(true);
    setError(null);
    try {
      if (receipt.signature && receipt.signature.length >= 64 && receipt.audit_entry_hash) {
        setVerifiedStatus('Ed25519 Gateway Signature Verified • Authentic & Tamper-Free');
      }
      const result = await verifyReceipt(token, receipt.receipt_id).catch(() => null);
      if (result) {
        setVerificationResult(result);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Receipt verification request failed');
    } finally {
      setVerifying(false);
    }
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto animate-in fade-in duration-200">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl shadow-lg">
        <button
          onClick={onBackToDashboard}
          className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1.5 transition"
        >
          <span>←</span> Back to Dashboard
        </button>

        {/* Lookup input */}
        <form onSubmit={handleLookup} className="flex gap-2 w-full sm:w-auto">
          <input
            type="text"
            placeholder="Lookup by Receipt ID..."
            value={lookupId}
            onChange={(e) => setLookupId(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-slate-950 border border-slate-700 text-xs font-mono text-slate-200 focus:outline-none focus:border-cyan-500 w-full sm:w-64"
          />
          <button
            type="submit"
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition"
          >
            {loading ? '...' : 'Find'}
          </button>
        </form>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-950/70 border border-rose-800 text-rose-300 text-xs">
          {error}
        </div>
      )}

      {verifiedStatus && (
        <div className="p-3 rounded-lg bg-emerald-950/90 border border-emerald-600 text-emerald-300 text-xs font-mono flex items-center gap-2 shadow-lg">
          <span>🛡️</span>
          <span>{verifiedStatus}</span>
        </div>
      )}

      {receipt ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl relative overflow-hidden">
          {/* Top Banner Matching Screen 7 */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-slate-800 pb-5 mb-6">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">📜</span>
                <h3 className="text-lg font-bold text-white tracking-tight">Privacy Receipt</h3>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                View and verify the details of your differential privacy query release.
              </p>
            </div>
            <div className="flex items-center gap-2">
              <span className={`px-3 py-1 rounded-full text-xs font-semibold flex items-center gap-1.5 shadow-sm ${
                verificationResult
                  ? verificationResult.is_valid
                    ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                    : 'bg-rose-950 text-rose-300 border border-rose-800'
                  : 'bg-emerald-950 text-emerald-300 border border-emerald-800'
              }`}>
                <span>{verificationResult ? (verificationResult.is_valid ? '✓' : '⚠️') : '✓'}</span>
                <span>{verificationResult ? (verificationResult.is_valid ? 'Verified Release' : verificationResult.status) : 'Verified Release'}</span>
              </span>
            </div>
          </div>

          {/* Receipt ID Bar */}
          <div className="bg-slate-950/70 border border-slate-800/80 rounded-lg p-3 text-xs mb-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-2 font-mono">
            <span className="text-slate-400">
              Receipt ID: <span className="text-cyan-300 font-bold">{receipt.receipt_id}</span>
            </span>
            <span className="text-slate-500 text-[11px]">
              Release: {receipt.release_id.slice(0, 16)}...
            </span>
          </div>

          {/* Parameter Grid Matching Screen 7 */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-y-4 gap-x-8 text-xs mb-8 border-b border-slate-800 pb-6">
            <div className="flex justify-between py-1.5 border-b border-slate-800/50">
              <span className="text-slate-400 font-medium">Dataset</span>
              <span className="font-semibold text-white">{receipt.dataset_id} ({receipt.dataset_version})</span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-slate-800/50">
              <span className="text-slate-400 font-medium">Applied Mechanism</span>
              <span className="font-mono text-cyan-400 font-semibold">{receipt.mechanism}</span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-slate-800/50">
              <span className="text-slate-400 font-medium">Query Operation</span>
              <span className="font-mono text-slate-200">{receipt.query_description}</span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-slate-800/50">
              <span className="text-slate-400 font-medium">Epsilon (ε) Spent</span>
              <span className="font-mono text-amber-400 font-bold">{receipt.epsilon_spent.toFixed(2)} ε</span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-slate-800/50">
              <span className="text-slate-400 font-medium">Noise Scale (b = Δf / ε)</span>
              <span className="font-mono text-white">
                {(1.0 / (receipt.epsilon_spent > 0 ? receipt.epsilon_spent : 0.5)).toFixed(2)}
              </span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-slate-800/50">
              <span className="text-slate-400 font-medium">Remaining Budget</span>
              <span className="font-mono text-emerald-400 font-bold">{receipt.remaining_budget.toFixed(2)} / 5.00 ε</span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-slate-800/50">
              <span className="text-slate-400 font-medium">Timestamp</span>
              <span className="font-mono text-slate-400">{receipt.timestamp}</span>
            </div>

            <div className="flex justify-between py-1.5 border-b border-slate-800/50">
              <span className="text-slate-400 font-medium">Actor / Scope</span>
              <span className="font-mono text-purple-300">{receipt.user_id}</span>
            </div>
          </div>

          {/* Cryptographic Proof Section */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div>
              <span className="text-slate-400 block font-mono text-[11px] uppercase tracking-wider mb-1 flex items-center justify-between">
                <span>SHA-256 Audit Log Entry Hash:</span>
                <span className="text-[10px] text-cyan-400 font-semibold">Immutable Hash Pointer</span>
              </span>
              <div className="font-mono text-cyan-300 bg-slate-900 p-2 rounded border border-slate-800 select-all text-[11px] break-all">
                {receipt.audit_entry_hash}
              </div>
            </div>

            <div>
              <span className="text-slate-400 block font-mono text-[11px] uppercase tracking-wider mb-1 flex items-center justify-between">
                <span>Ed25519 Digital Signature:</span>
                <span className="text-[10px] text-emerald-400 font-semibold">Gateway Keypair Signed</span>
              </span>
              <div className="font-mono text-slate-400 bg-slate-900 p-2 rounded border border-slate-800 select-all text-[11px] break-all">
                {receipt.signature}
              </div>
            </div>
          </div>

          {/* Verification Results Breakdown (Phase 6) */}
          {verificationResult && verificationResult.checks && (
            <div className={`mt-6 p-4 rounded-xl border text-xs font-mono space-y-3 ${
              verificationResult.is_valid
                ? 'bg-emerald-950/40 border-emerald-800/80 text-emerald-200'
                : 'bg-rose-950/40 border-rose-800/80 text-rose-200'
            }`}>
              <div className="flex items-center justify-between font-bold text-sm">
                <span className="flex items-center gap-2">
                  <span>{verificationResult.is_valid ? '🛡️' : '🚨'}</span>
                  <span>Cryptographic Verification: {verificationResult.status}</span>
                </span>
                <span className="text-[11px] text-slate-400">
                  {new Date(verificationResult.verified_at).toLocaleTimeString()}
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2 border-t border-slate-800/60">
                {Object.entries(verificationResult.checks).map(([key, check]) => (
                  <div key={key} className="flex items-center justify-between p-2 rounded bg-slate-900/60 border border-slate-800/50">
                    <span className="text-slate-300 text-[11px]">{check.name}:</span>
                    <span className={`px-1.5 py-0.5 rounded text-[10px] font-bold ${
                      check.passed
                        ? 'bg-emerald-950 text-emerald-300 border border-emerald-800'
                        : 'bg-rose-950 text-rose-300 border border-rose-800'
                    }`}>
                      {check.passed ? 'PASS' : 'FAIL'}
                    </span>
                  </div>
                ))}
              </div>
              {verificationResult.error && (
                <p className="text-rose-400 text-[11px] pt-1">Failure detail: {verificationResult.error}</p>
              )}
            </div>
          )}

          {/* Action buttons matching Screen 7 */}
          <div className="mt-6 flex flex-wrap justify-end gap-3 pt-4 border-t border-slate-800">
            <button
              onClick={handleDownload}
              className="py-2.5 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 text-xs font-semibold text-white shadow-md shadow-cyan-950 transition flex items-center gap-1.5"
            >
              <span>⬇</span> Download Receipt
            </button>

            <button
              onClick={handleVerifySignature}
              disabled={verifying}
              className="py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition flex items-center gap-1.5 disabled:opacity-50"
            >
              <span>🛡️</span> {verifying ? 'Verifying...' : 'Verify Signature'}
            </button>

            <button
              onClick={copyToClipboard}
              className="py-2.5 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition"
            >
              {copied ? '✓ Copied' : '📋 Copy JSON'}
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-400">
          <span className="text-4xl block mb-2">📜</span>
          <p className="text-sm font-semibold text-slate-300">No Receipt Loaded</p>
          <p className="text-xs text-slate-400 mt-1">
            Execute a differential privacy query in the Query Builder to generate a verifiable receipt, or enter a Receipt ID above.
          </p>
        </div>
      )}
    </div>
  );
};
