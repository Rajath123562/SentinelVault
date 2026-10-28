import React, { useState } from 'react';
import { PrivacyReceipt } from '../types/system';
import { getReceipt } from '../services/api';

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
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const handleLookup = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!lookupId.trim()) return;
    setLoading(true);
    setError(null);
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

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      {/* Header bar */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 bg-slate-900 border border-slate-800 p-4 rounded-xl">
        <button
          onClick={onBackToDashboard}
          className="text-xs font-semibold text-cyan-400 hover:text-cyan-300 flex items-center gap-1.5 transition"
        >
          <span>←</span> Back to Analytics Dashboard
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

      {receipt ? (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-8 shadow-2xl relative overflow-hidden">
          {/* Top Banner */}
          <div className="flex items-center justify-between border-b border-slate-800 pb-5 mb-6">
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xl">📜</span>
                <h3 className="text-lg font-bold text-white">Cryptographic Privacy Receipt</h3>
              </div>
              <p className="text-xs text-slate-400 mt-1">
                Verifiable cryptographic proof of differential privacy expenditure and audit ledger inclusion
              </p>
            </div>
            <span className="px-3 py-1 rounded-full text-xs font-semibold bg-emerald-950 text-emerald-300 border border-emerald-800 flex items-center gap-1.5">
              <span>✓</span> {receipt.policy_check_status}
            </span>
          </div>

          {/* Receipt Properties Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6 text-xs mb-8">
            <div className="space-y-4">
              <div>
                <span className="text-slate-400 block font-medium uppercase tracking-wider text-[11px] mb-1">
                  Receipt Identifier
                </span>
                <span className="font-mono text-cyan-300 bg-slate-950 px-2.5 py-1 rounded border border-slate-800 select-all block">
                  {receipt.receipt_id}
                </span>
              </div>

              <div>
                <span className="text-slate-400 block font-medium uppercase tracking-wider text-[11px] mb-1">
                  Associated Release ID
                </span>
                <span className="font-mono text-slate-300 bg-slate-950 px-2.5 py-1 rounded border border-slate-800 select-all block">
                  {receipt.release_id}
                </span>
              </div>

              <div>
                <span className="text-slate-400 block font-medium uppercase tracking-wider text-[11px] mb-1">
                  Authenticated User & Scope
                </span>
                <div className="flex gap-2">
                  <span className="font-mono text-slate-300 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                    User: {receipt.user_id}
                  </span>
                  <span className="font-mono text-purple-300 bg-slate-950 px-2 py-0.5 rounded border border-slate-800">
                    Dataset: {receipt.dataset_id} ({receipt.dataset_version})
                  </span>
                </div>
              </div>

              <div>
                <span className="text-slate-400 block font-medium uppercase tracking-wider text-[11px] mb-1">
                  Query Description
                </span>
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-slate-200 font-mono">
                  {receipt.query_description}
                </div>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <span className="text-slate-400 block font-medium uppercase tracking-wider text-[11px] mb-1">
                  Applied Privacy Mechanism
                </span>
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-cyan-400 font-mono">
                  {receipt.mechanism}
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-center">
                  <span className="text-slate-400 block text-[10px] uppercase">ε Spent</span>
                  <span className="font-mono font-bold text-white text-sm">{receipt.epsilon_spent.toFixed(2)}</span>
                </div>
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-center">
                  <span className="text-slate-400 block text-[10px] uppercase">Cumulative ε</span>
                  <span className="font-mono font-bold text-amber-300 text-sm">{receipt.cumulative_epsilon.toFixed(2)}</span>
                </div>
                <div className="p-2.5 rounded bg-slate-950 border border-slate-800 text-center">
                  <span className="text-slate-400 block text-[10px] uppercase">Remaining ε</span>
                  <span className="font-mono font-bold text-emerald-400 text-sm">{receipt.remaining_budget.toFixed(2)}</span>
                </div>
              </div>

              <div>
                <span className="text-slate-400 block font-medium uppercase tracking-wider text-[11px] mb-1">
                  Issuance Timestamp
                </span>
                <span className="font-mono text-slate-400 bg-slate-950 px-2 py-1 rounded border border-slate-800 block">
                  {receipt.timestamp}
                </span>
              </div>
            </div>
          </div>

          {/* Cryptographic Proof Section */}
          <div className="p-4 rounded-xl bg-slate-950 border border-slate-800 space-y-3">
            <div>
              <span className="text-slate-400 block font-mono text-[11px] uppercase tracking-wider mb-1 flex items-center justify-between">
                <span>SHA-256 Audit Log Entry Hash:</span>
                <span className="text-[10px] text-cyan-400">Hash Pointer</span>
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

          {/* Action buttons */}
          <div className="mt-6 flex justify-end gap-3">
            <button
              onClick={copyToClipboard}
              className="py-2 px-4 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition"
            >
              {copied ? '✓ Copied JSON' : '📋 Copy Receipt JSON'}
            </button>
          </div>
        </div>
      ) : (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-400">
          <span className="text-4xl block mb-2">📜</span>
          <p className="text-sm font-semibold text-slate-300">No Receipt Loaded</p>
          <p className="text-xs text-slate-400 mt-1">
            Execute a differential privacy query in the Analytics Dashboard to generate a verifiable receipt, or enter a Receipt ID above.
          </p>
        </div>
      )}
    </div>
  );
};
