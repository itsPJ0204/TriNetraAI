import React, { useState } from 'react';
import { Check, X, PlaneTakeoff, ShieldAlert } from 'lucide-react';
import { INITIAL_AUDIT_LOG } from '../data/mockData';
import { submitReview } from '../services/api';

export default function AnalystReview({ activeTile }) {
  const [auditLog, setAuditLog] = useState(() => {
    try {
      const saved = localStorage.getItem('sat_intel_audit_log');
      if (saved) return JSON.parse(saved);
    } catch (e) {}
    return INITIAL_AUDIT_LOG;
  });
  const [feedback, setFeedback] = useState(null);

  const handleDecision = async (decision) => {
    if (!activeTile) return;
    const res = await submitReview(
      activeTile.id,
      decision,
      `Analyst triage for ${activeTile.sensor} pass over ${activeTile.coordinates.formatted}`
    );
    if (res.success) {
      setAuditLog(prev => [res.auditEntry, ...prev]);
      setFeedback(`Recorded decision [${decision}] for Tile ${activeTile.id} in cryptographic audit ledger.`);
      setTimeout(() => setFeedback(null), 4000);
    }
  };

  return (
    <section className="w-full py-16 px-4 sm:px-6 lg:px-8 max-w-7xl mx-auto pb-28" id="audit-log">
      <div className="flex items-center gap-2 mb-2">
        <span className="w-2 h-2 bg-[#00e5ff]"></span>
        <span className="font-mono text-[10px] text-[#00e5ff] uppercase tracking-widest font-semibold">
          MODULE // 05
        </span>
      </div>
      <h2 className="text-[28px] sm:text-[34px] font-bold text-white tracking-tight mb-2">
        Analyst Decision Queue & Air-Gapped Provenance Ledger
      </h2>
      <p className="text-[14px] text-[#94a3b8] mb-8">
        Cryptographic audit trail with instant triage escalation and local immutable verification.
      </p>

      {/* Operational Action Buttons Cluster */}
      <div className="bg-[#0d1726] border border-[#1e293b] p-4 sm:p-6 rounded-sm mb-8">
        <div className="flex flex-col md:flex-row items-center justify-between gap-4">
          <div>
            <h3 className="font-mono text-[13px] font-bold text-white uppercase tracking-wider">
              MISSION TARGET TRIAGE // ACTIVE TILE: {activeTile?.id || 'T027'}
            </h3>
            <p className="text-[12px] text-[#94a3b8] mt-0.5 font-sans">
              Sign-off triggers offline export to tactical field terminals via secure air-gapped data diode.
            </p>
          </div>

          <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
            {/* Button 1: Approve Target */}
            <button
              type="button"
              onClick={() => handleDecision('APPROVED')}
              className="px-5 py-2.5 bg-[#00a572] hover:bg-[#10b981] text-[#070e1b] font-mono text-[11px] font-bold uppercase tracking-wider transition-all flex items-center gap-2 shadow-[0_0_12px_rgba(16,185,129,0.3)] cursor-pointer"
            >
              <Check className="w-4 h-4" />
              [ APPROVE TARGET INTEL ]
            </button>

            {/* Button 2: Reject False Positive */}
            <button
              type="button"
              onClick={() => handleDecision('REJECTED_FP')}
              className="px-5 py-2.5 bg-[#93000a]/30 hover:bg-[#93000a]/60 text-[#ffb4ab] border border-[#ef4444] font-mono text-[11px] font-bold uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer"
            >
              <X className="w-4 h-4" />
              [ REJECT FALSE POSITIVE ]
            </button>

            {/* Button 3: Escalate Recon */}
            <button
              type="button"
              onClick={() => handleDecision('ESCALATED')}
              className="px-5 py-2.5 bg-[#f59e0b]/20 hover:bg-[#f59e0b]/30 text-[#f59e0b] border border-[#f59e0b]/50 font-mono text-[11px] font-bold uppercase tracking-wider transition-all flex items-center gap-2 cursor-pointer"
            >
              <PlaneTakeoff className="w-4 h-4" />
              [ ESCALATE / AIR RECON ]
            </button>
          </div>
        </div>

        {/* Action feedback banner */}
        {feedback && (
          <div className="mt-4 p-2.5 bg-[#00e5ff]/10 border border-[#00e5ff] text-[#00e5ff] font-mono text-[11px] rounded-sm flex items-center gap-2">
            <ShieldAlert className="w-4 h-4" />
            <span>{feedback}</span>
          </div>
        )}
      </div>

      {/* Offline Audit Logging Table */}
      <div className="bg-[#0d1726]/80 border border-[#1e293b] rounded-sm overflow-hidden">
        <div className="px-4 py-3 bg-[#131f33] border-b border-[#1e293b] flex items-center justify-between font-mono text-[11px] text-[#64748b]">
          <span className="font-bold text-[#9cf0ff] uppercase tracking-wider">
            OFFLINE PROVENANCE AUDIT LOG (LOCAL FAISS STORE)
          </span>
          <span>SECURITY ENCLAVE // LEVEL 4</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left font-mono text-[11px]">
            <thead className="bg-[#070e1b] text-[#64748b] border-b border-[#1e293b] uppercase text-[10px]">
              <tr>
                <th className="py-2.5 px-4">TIMESTAMP (IST)</th>
                <th className="py-2.5 px-4">TARGET ID</th>
                <th className="py-2.5 px-4">ANALYST SIGN-OFF</th>
                <th className="py-2.5 px-4">SHA-256 PROVENANCE HASH</th>
                <th className="py-2.5 px-4 text-right">STATUS</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#1e293b]/60 text-[#94a3b8]">
              {auditLog.map((row, i) => (
                <tr key={i} className="hover:bg-[#1a2942]/40 transition-colors">
                  <td className="py-3 px-4 text-white">{row.timestamp}</td>
                  <td className="py-3 px-4 text-[#00e5ff] font-semibold">{row.tileId}</td>
                  <td className="py-3 px-4">{row.operator}</td>
                  <td className="py-3 px-4 text-[#64748b] font-mono text-[10px]">
                    {row.sha256.substring(0, 12)}...{row.sha256.substring(56)}
                  </td>
                  <td className="py-3 px-4 text-right">
                    <span
                      className={`px-2 py-0.5 text-[9px] font-bold uppercase rounded-sm border ${
                        row.decision.includes('APPROVE')
                          ? 'bg-[#10b981]/20 text-[#10b981] border-[#10b981]/40'
                          : row.decision.includes('REJECT')
                          ? 'bg-[#ef4444]/20 text-[#ef4444] border-[#ef4444]/40'
                          : 'bg-[#f59e0b]/20 text-[#f59e0b] border-[#f59e0b]/40'
                      }`}
                    >
                      {row.decision}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
