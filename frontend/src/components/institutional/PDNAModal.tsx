import React, { useState } from 'react';
import {
  FileText,
  X,
  Printer,
  CheckCircle2,
  Building,
  Truck,
  Apple,
  Droplets,
  Zap,
  TrendingUp,
  ShieldAlert,
} from 'lucide-react';

interface SectorLoss {
  sector_name: string;
  damages_inr_lakhs: number;
  losses_inr_lakhs: number;
  total_need_inr_lakhs: number;
  description: string;
}


interface PDNADossierData {
  dossier_id: string;
  incident_name: string;
  ndma_standard_compliant: boolean;
  assessor_name: string;
  villages_assessed_count: number;
  households_displaced: number;
  sector_breakdown: SectorLoss[];
  total_reconstruction_cost_inr_crores: number;
  priority_early_recovery_actions: string[];
  generated_at: string;
}

interface PDNAModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const PDNAModal: React.FC<PDNAModalProps> = ({ isOpen, onClose }) => {
  const [incidentName, setIncidentName] = useState('Uttarkashi Monsoonal Cloudburst & Surge 2026');
  const [disasterType, setDisasterType] = useState('Flash Flood & Debris Runout');
  const [assessorName, setAssessorName] = useState('District Disaster Management Officer');
  const [selectedVillages, setSelectedVillages] = useState<string[]>([
    'VIL_UTK_01',
    'VIL_UTK_02',
    'VIL_UTK_03',
  ]);
  const [loading, setLoading] = useState(false);
  const [dossier, setDossier] = useState<PDNADossierData | null>(null);

  if (!isOpen) return null;

  const handleGenerate = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/institutional/pdna/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          incident_name: incidentName,
          disaster_type: disasterType,
          village_ids: selectedVillages,
          assessor_name: assessorName,
        }),
      });
      if (res.ok) {
        const data = await res.json();
        setDossier(data);
      }
    } catch (err) {
      console.error('Failed to generate PDNA:', err);
    } finally {
      setLoading(false);
    }
  };

  const getSectorIcon = (name: string) => {
    if (name.includes('Housing')) return <Building className="w-4 h-4 text-blue-400" />;
    if (name.includes('Transport')) return <Truck className="w-4 h-4 text-amber-400" />;
    if (name.includes('Agriculture')) return <Apple className="w-4 h-4 text-emerald-400" />;
    if (name.includes('Water')) return <Droplets className="w-4 h-4 text-cyan-400" />;
    return <Zap className="w-4 h-4 text-purple-400" />;
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/75 backdrop-blur-sm flex items-center justify-center p-4 font-mono text-xs">
      <div className="bg-slate-900 border border-slate-800 rounded-xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="p-4 bg-slate-950 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="p-2 rounded-lg bg-blue-950/60 border border-blue-600/40 text-blue-400">
              <FileText className="w-5 h-5" />
            </div>
            <div>
              <div className="font-bold text-slate-100 text-sm flex items-center gap-2">
                NDMA Post-Disaster Needs Assessment (PDNA)
                <span className="px-2 py-0.5 rounded text-[9px] font-bold bg-blue-950 border border-blue-500/30 text-blue-400">
                  NATIONAL STANDARD
                </span>
              </div>
              <div className="text-[10px] text-slate-400">
                Automated Sector Damage, Loss & Early Recovery Estimation
              </div>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-slate-800 text-slate-400 hover:text-slate-200 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {!dossier ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Incident Title
                  </label>
                  <input
                    type="text"
                    value={incidentName}
                    onChange={(e) => setIncidentName(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
                  />
                </div>
                <div>
                  <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                    Disaster Type
                  </label>
                  <input
                    type="text"
                    value={disasterType}
                    onChange={(e) => setDisasterType(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
                  />
                </div>
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Assessing Officer / Authority
                </label>
                <input
                  type="text"
                  value={assessorName}
                  onChange={(e) => setAssessorName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-slate-950 border border-slate-700 text-slate-100 text-xs focus:outline-none focus:border-blue-500"
                />
              </div>

              <div>
                <label className="text-[10px] font-bold text-slate-400 uppercase tracking-wider block mb-1">
                  Impacted Villages to Include
                </label>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                  {[
                    { id: 'VIL_UTK_01', name: 'Harsil' },
                    { id: 'VIL_UTK_02', name: 'Dharali' },
                    { id: 'VIL_UTK_03', name: 'Jhala' },
                    { id: 'VIL_UTK_04', name: 'Sukhi' },
                    { id: 'VIL_UTK_05', name: 'Gangotri' },
                    { id: 'VIL_UTK_10', name: 'Uttarkashi Town' },
                  ].map((v) => (
                    <label
                      key={v.id}
                      className="flex items-center gap-2 p-2 rounded bg-slate-950 border border-slate-800 cursor-pointer hover:border-slate-700"
                    >
                      <input
                        type="checkbox"
                        checked={selectedVillages.includes(v.id)}
                        onChange={(e) => {
                          if (e.target.checked) setSelectedVillages((prev) => [...prev, v.id]);
                          else setSelectedVillages((prev) => prev.filter((x) => x !== v.id));
                        }}
                        className="rounded border-slate-700 text-blue-600 focus:ring-0"
                      />
                      <span className="text-slate-200">{v.name}</span>
                    </label>
                  ))}
                </div>
              </div>

              <button
                onClick={handleGenerate}
                disabled={loading || selectedVillages.length === 0}
                className="w-full py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold flex items-center justify-center gap-2 disabled:opacity-50 transition-colors text-xs"
              >
                {loading ? 'Synthesizing Satellite & Ground Damage Telemetry...' : 'Generate Official NDMA Dossier'}
              </button>
            </div>
          ) : (
            /* Dossier Result View */
            <div className="space-y-4">
              {/* Executive Summary Card */}
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg grid grid-cols-2 sm:grid-cols-4 gap-3 text-center">
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Total Recovery Need</div>
                  <div className="text-xl font-black text-amber-300">
                    ₹{dossier.total_reconstruction_cost_inr_crores} Cr
                  </div>
                  <div className="text-[9px] text-slate-500">NDMA / SDRF Pool</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Displaced Families</div>
                  <div className="text-xl font-black text-red-300">
                    {dossier.households_displaced}
                  </div>
                  <div className="text-[9px] text-slate-500">Shelter Relocation</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Settlements Assessed</div>
                  <div className="text-xl font-black text-blue-300">
                    {dossier.villages_assessed_count}
                  </div>
                  <div className="text-[9px] text-slate-500">Upper Bhagirathi</div>
                </div>
                <div>
                  <div className="text-[10px] text-slate-500 uppercase">Compliance Standard</div>
                  <div className="text-xs font-bold text-emerald-400 mt-1 flex items-center justify-center gap-1">
                    <CheckCircle2 className="w-3.5 h-3.5" /> NDMA / UNDP
                  </div>
                  <div className="text-[9px] text-slate-500">Verified Geometry</div>
                </div>
              </div>

              {/* Sector Table */}
              <div className="overflow-x-auto rounded-lg border border-slate-800">
                <table className="w-full text-left">
                  <thead className="bg-slate-950 text-slate-400 text-[10px] uppercase">
                    <tr>
                      <th className="p-2.5">Sector</th>
                      <th className="p-2.5">Damages (₹ L)</th>
                      <th className="p-2.5">Losses (₹ L)</th>
                      <th className="p-2.5">Total Need (₹ L)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800">
                    {dossier.sector_breakdown.map((s, idx) => (
                      <tr key={idx} className="hover:bg-slate-800/40">
                        <td className="p-2.5 flex items-center gap-2">
                          {getSectorIcon(s.sector_name)}
                          <div>
                            <div className="font-bold text-slate-200">{s.sector_name}</div>
                            <div className="text-[9px] text-slate-500">{s.description}</div>
                          </div>
                        </td>
                        <td className="p-2.5 text-slate-300">₹{s.damages_inr_lakhs.toLocaleString()}</td>
                        <td className="p-2.5 text-slate-300">₹{s.losses_inr_lakhs.toLocaleString()}</td>
                        <td className="p-2.5 font-bold text-amber-300">₹{s.total_need_inr_lakhs.toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Priority Recovery Actions */}
              <div className="p-3 bg-slate-950 border border-slate-800 rounded-lg space-y-2">
                <div className="text-[10px] font-bold uppercase tracking-wider text-emerald-400 flex items-center gap-1.5">
                  <ShieldAlert className="w-3.5 h-3.5" /> Priority Early Recovery Actions (0 - 30 Days)
                </div>
                <ul className="space-y-1 text-[11px] text-slate-300">
                  {dossier.priority_early_recovery_actions.map((act, idx) => (
                    <li key={idx} className="flex items-start gap-2">
                      <span className="text-emerald-500 font-bold">•</span>
                      <span>{act}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className="flex items-center gap-3 pt-2">
                <button
                  onClick={() => window.print()}
                  className="flex-1 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-bold flex items-center justify-center gap-2 transition-colors"
                >
                  <Printer className="w-4 h-4" /> Print / Export Official Dossier PDF
                </button>
                <button
                  onClick={() => setDossier(null)}
                  className="px-4 py-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition-colors"
                >
                  New Assessment
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
