import React from 'react';
import { ShieldCheck, CheckCircle2, AlertTriangle, Cpu } from 'lucide-react';

export const SensorTrustPanel: React.FC = () => {
  const signalAgreement = [
    { source: 'In-Situ Rain Gauges (4 Nodes)', agreement: 96, status: 'HIGH CONSENSUS' },
    { source: 'Ridge Soil Saturation Probes', agreement: 91, status: 'HIGH CONSENSUS' },
    { source: 'Bhagirathi River Stage Gauges', agreement: 88, status: 'VERIFIED' },
    { source: 'Satellite GPM / IMD Radar Nowcast', agreement: 84, status: 'ALIGNED' },
  ];

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 font-mono text-xs select-none shadow-md">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-3">
        <div className="flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-emerald-400" />
          <div>
            <div className="font-bold text-slate-100 text-sm">Sensor Network Trust & Validation</div>
            <div className="text-[10px] text-slate-400">Multi-source cross-verification layer</div>
          </div>
        </div>
        <div className="text-right">
          <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 font-bold">
            CONFIDENCE: 92.4% (HIGH)
          </span>
        </div>
      </div>

      {/* Multi-Source Cross Validation Rows */}
      <div className="space-y-2 mb-3">
        {signalAgreement.map((sig) => (
          <div key={sig.source} className="flex items-center justify-between p-2 rounded bg-slate-950/60 border border-slate-800/80">
            <div className="flex items-center gap-2">
              <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
              <span className="text-slate-300">{sig.source}</span>
            </div>
            <div className="flex items-center gap-2">
              <div className="w-20 bg-slate-800 h-1.5 rounded-full overflow-hidden">
                <div className="bg-emerald-400 h-full rounded-full" style={{ width: `${sig.agreement}%` }} />
              </div>
              <span className="font-bold text-slate-200">{sig.agreement}%</span>
            </div>
          </div>
        ))}
      </div>

      {/* Sensor Anomaly Alert */}
      <div className="p-3 rounded-lg bg-purple-950/30 border border-purple-800/40 text-[11px] text-purple-200 flex items-start gap-2">
        <AlertTriangle className="w-4 h-4 text-purple-400 shrink-0 mt-0.5" />
        <div>
          <strong className="text-purple-300 block font-bold">Isolated Telemetry Anomaly (Filtered from ML Trigger):</strong>
          <span className="text-slate-300 leading-tight">
            Soil probe <code>#SNS_SM_JSH_01</code> at Joshiyara indicates 12% moisture despite heavy rainfall. Isolated by spatial consensus engine to prevent false negative.
          </span>
        </div>
      </div>
    </div>
  );
};
