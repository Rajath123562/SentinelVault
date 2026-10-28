import React, { useState, useEffect, useCallback } from 'react';
import { 
  AuditVerificationResponse, 
  EvaluationStatusResponse 
} from '../types/system';
import { 
  verifyAuditLedger, 
  getEvaluationStatus 
} from '../services/api';

interface AuditEvaluationViewProps {
  token: string;
}

export const AuditEvaluationView: React.FC<AuditEvaluationViewProps> = ({ token }) => {
  const [auditResult, setAuditResult] = useState<AuditVerificationResponse | null>(null);
  const [evalStatus, setEvalStatus] = useState<EvaluationStatusResponse | null>(null);
  const [verifying, setVerifying] = useState(false);
  const [loadingEval, setLoadingEval] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const runVerification = useCallback(async () => {
    setVerifying(true);
    setError(null);
    try {
      const data = await verifyAuditLedger(token);
      setAuditResult(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Audit verification failed');
    } finally {
      setVerifying(false);
    }
  }, [token]);

  const loadEvaluation = useCallback(async () => {
    setLoadingEval(true);
    try {
      const data = await getEvaluationStatus(token);
      setEvalStatus(data);
    } catch (err: unknown) {
      console.error('Failed to load evaluation status', err);
    } finally {
      setLoadingEval(false);
    }
  }, [token]);

  useEffect(() => {
    runVerification();
    loadEvaluation();
  }, [runVerification, loadEvaluation]);

  const benchmarkReport = evalStatus?.benchmark_report;

  return (
    <div className="space-y-8 max-w-5xl mx-auto">
      {/* Cryptographic Audit Verification Card */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-slate-800 pb-4 mb-6">
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl">🛡️</span>
              <h3 className="text-lg font-bold text-white">Cryptographic Audit Chain Verification</h3>
            </div>
            <p className="text-xs text-slate-400 mt-1">
              Verifies mathematical linkage across all recorded query releases using SHA-256 pointers & Ed25519 digital signatures.
            </p>
          </div>

          <button
            onClick={runVerification}
            disabled={verifying}
            className="py-2 px-4 rounded-lg bg-cyan-600 hover:bg-cyan-500 font-semibold text-white text-xs shadow-md shadow-cyan-950 transition disabled:opacity-50"
          >
            {verifying ? 'Verifying Ledger...' : '🔄 Re-verify Audit Ledger'}
          </button>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-rose-950/70 border border-rose-800 text-rose-300 text-xs">
            {error}
          </div>
        )}

        {auditResult && (
          <div className="space-y-4">
            <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 p-4 rounded-lg bg-slate-950 border border-slate-800">
              <div className="flex items-center gap-3">
                <span className="text-2xl">
                  {auditResult.valid && !auditResult.tamper_detected ? '✅' : '🚨'}
                </span>
                <div>
                  <div className="font-bold text-sm text-white">
                    {auditResult.valid && !auditResult.tamper_detected
                      ? 'AUDIT CHAIN INTEGRITY VERIFIED'
                      : 'TAMPER DETECTED IN AUDIT LEDGER'}
                  </div>
                  <div className="text-xs text-slate-400">
                    {auditResult.total_entries > 0
                      ? `${auditResult.verified_entries} of ${auditResult.total_entries} entries verified without modification`
                      : 'Audit ledger is currently empty (0 entries recorded)'}
                  </div>
                </div>
              </div>

              <div className="text-right">
                <span className="px-3 py-1 rounded text-xs font-mono font-semibold bg-slate-900 border border-slate-700 text-cyan-300">
                  {auditResult.algorithm}
                </span>
              </div>
            </div>

            {auditResult.tamper_detected && (
              <div className="p-4 rounded-lg bg-rose-950/80 border border-rose-700 text-rose-200 text-xs">
                <span className="font-bold block mb-1">Security Alert: Data Modification Detected</span>
                <p>{auditResult.error_message}</p>
                {auditResult.broken_at_entry && (
                  <p className="mt-1 font-mono">Chain broken at Entry ID: {auditResult.broken_at_entry}</p>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Utility vs Privacy Empirical Benchmark */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl">
        <div className="border-b border-slate-800 pb-4 mb-6">
          <div className="flex items-center gap-2">
            <span className="text-xl">📈</span>
            <h3 className="text-lg font-bold text-white">Empirical Privacy-Utility Trade-off Benchmark</h3>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Empirical evaluation over 50 randomized trials per epsilon on synthetic records, compared directly against exact non-private ground truth.
          </p>
        </div>

        {benchmarkReport?.overall_summary_by_epsilon ? (
          <div className="space-y-6">
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border border-slate-800 rounded-lg overflow-hidden">
                <thead className="bg-slate-950 text-slate-300 uppercase tracking-wider font-mono">
                  <tr>
                    <th className="py-3 px-4">Privacy Level (ε)</th>
                    <th className="py-3 px-4">Mean Abs Error (MAE)</th>
                    <th className="py-3 px-4">Root Mean Sq Error (RMSE)</th>
                    <th className="py-3 px-4">Relative Error (%)</th>
                    <th className="py-3 px-4">Privacy Guarantee</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/80 font-mono text-slate-300 bg-slate-900">
                  {Object.entries(benchmarkReport.overall_summary_by_epsilon).map(([eps, metrics]) => (
                    <tr key={eps} className="hover:bg-slate-800/50">
                      <td className="py-3 px-4 font-bold text-cyan-400">{eps}</td>
                      <td className="py-3 px-4">{metrics.avg_mae.toFixed(2)}</td>
                      <td className="py-3 px-4">{metrics.avg_rmse.toFixed(2)}</td>
                      <td className="py-3 px-4 font-semibold text-emerald-400">
                        {metrics.avg_rel_error_pct.toFixed(2)}%
                      </td>
                      <td className="py-3 px-4 font-sans text-slate-400">
                        {parseFloat(eps) <= 0.2
                          ? 'High privacy protection (strong plausible deniability)'
                          : 'High analytical utility (low relative perturbation)'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="p-4 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-300 space-y-2">
              <span className="font-semibold text-white block">Key Empirical Conclusions:</span>
              <ul className="list-disc list-inside space-y-1 text-slate-400">
                {benchmarkReport.conclusions.map((c, i) => (
                  <li key={i}>{c}</li>
                ))}
              </ul>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-slate-400 text-xs">
            {loadingEval ? 'Loading benchmark metrics...' : 'Benchmark report currently being compiled.'}
          </div>
        )}
      </div>

      {/* Official Status and Transparency Disclosure */}
      <div className="bg-slate-900 border border-amber-900/50 rounded-xl p-6 shadow-xl">
        <h4 className="text-sm font-bold text-amber-300 uppercase tracking-wider mb-3 flex items-center gap-2">
          <span>⚠️</span> Official Competition Conformance & Evaluation Notice
        </h4>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs font-mono">
          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-400 block text-[11px] mb-1">Official Accounting Spec Status:</span>
            <span className="text-amber-400 font-bold">
              {evalStatus?.official_accounting_spec_status ?? 'DEMO ACCOUNTING ACTIVE — OFFICIAL CONFORMANCE NOT VERIFIED'}
            </span>
          </div>

          <div className="p-3 rounded-lg bg-slate-950 border border-slate-800">
            <span className="text-slate-400 block text-[11px] mb-1">Official Empirical Risk Evaluation:</span>
            <span className="text-rose-400 font-bold">
              {evalStatus?.official_empirical_risk_evaluation_status ?? 'OFFICIAL EMPIRICAL RISK EVALUATION NOT CONFIGURED'}
            </span>
          </div>
        </div>

        <p className="text-xs text-slate-400 mt-4 leading-relaxed">
          In strict compliance with our Anti-Fakery and Integrity Contract, HOTFIX operates using an exact integer micro-epsilon ledger and standard Laplace mechanism. We do not invent official competition scoring, attack harness outputs, or third-party evaluations until the official Track 4 evaluation harness is supplied.
        </p>
      </div>
    </div>
  );
};
