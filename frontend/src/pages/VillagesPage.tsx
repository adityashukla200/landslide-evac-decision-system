import React, { useState } from 'react';
import { useEmergency } from '../context/EmergencyContext';
import { RiskBadge } from '../components/common/RiskBadge';
import { Village } from '../types';
import { Search, Filter, Mountain, Users, Clock, AlertOctagon } from 'lucide-react';

export const VillagesPage: React.FC = () => {
  const { villages, setSelectedVillage } = useEmergency();
  const [searchTerm, setSearchTerm] = useState('');
  const [tierFilter, setTierFilter] = useState<string>('ALL');

  const filtered = villages.filter((v) => {
    const matchesSearch =
      v.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      v.id.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesTier = tierFilter === 'ALL' || v.risk.tier === tierFilter;
    return matchesSearch && matchesTier;
  });

  return (
    <div className="flex-1 p-4 md:p-6 bg-slate-950 overflow-y-auto font-mono text-xs select-none space-y-4">
      {/* Header & Controls */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 font-mono">VILLAGE & WARD DOSSIER</h2>
          <p className="text-xs text-slate-400">
            Real-time slope stability, nowcast precipitation, and evacuation status across Uttarkashi
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Search Input */}
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800">
            <Search className="w-3.5 h-3.5 text-slate-400" />
            <input
              type="text"
              placeholder="Search village or ward..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="bg-transparent text-xs text-slate-200 outline-none w-44"
            />
          </div>

          {/* Tier Filter */}
          <div className="flex items-center gap-1.5 bg-slate-900 px-2 py-1.5 rounded-lg border border-slate-800">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={tierFilter}
              onChange={(e) => setTierFilter(e.target.value)}
              className="bg-transparent text-xs text-slate-300 outline-none cursor-pointer"
            >
              <option value="ALL" className="bg-slate-900">All Tiers ({villages.length})</option>
              <option value="EVACUATE" className="bg-slate-900">EVACUATE ({villages.filter(v => v.risk.tier === 'EVACUATE').length})</option>
              <option value="WARNING" className="bg-slate-900">WARNING ({villages.filter(v => v.risk.tier === 'WARNING').length})</option>
              <option value="WATCH" className="bg-slate-900">WATCH ({villages.filter(v => v.risk.tier === 'WATCH').length})</option>
              <option value="NONE" className="bg-slate-900">SAFE ({villages.filter(v => v.risk.tier === 'NONE').length})</option>
            </select>
          </div>
        </div>
      </div>

      {/* Villages Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
        {filtered.map((v) => {
          const { risk, explanation } = { risk: v.risk, explanation: v.risk.explanation };

          return (
            <div
              key={v.id}
              onClick={() => setSelectedVillage(v)}
              className="p-4 rounded-xl bg-slate-900 border border-slate-800 hover:border-slate-700 transition-all cursor-pointer shadow-md space-y-3"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-bold text-slate-100 text-sm">{v.name}</h3>
                  <div className="text-[10px] text-slate-400 flex items-center gap-1.5 mt-0.5">
                    <Mountain className="w-3 h-3 text-slate-500" /> Elev: {v.elevationM}m • {v.district}
                  </div>
                </div>
                <RiskBadge tier={risk.tier} size="sm" />
              </div>

              {/* Mini Metrics */}
              <div className="grid grid-cols-3 gap-1.5 text-center p-2 rounded-lg bg-slate-950/80 border border-slate-800/80 text-[10px]">
                <div>
                  <span className="text-slate-500 block">PROBABILITY</span>
                  <strong className="text-slate-200 font-bold text-xs">{(risk.probability * 100).toFixed(0)}%</strong>
                </div>
                <div>
                  <span className="text-slate-500 block">FOS</span>
                  <strong
                    className={`font-bold text-xs ${
                      explanation.factorOfSafety < 1.0 ? 'text-red-400' : 'text-emerald-400'
                    }`}
                  >
                    {explanation.factorOfSafety.toFixed(2)}
                  </strong>
                </div>
                <div>
                  <span className="text-slate-500 block">LEAD TIME</span>
                  <strong className="text-orange-400 font-bold text-xs">~{risk.leadTimeMinutes}m</strong>
                </div>
              </div>

              {/* Environmental Indicators */}
              <div className="text-[11px] text-slate-400 space-y-1 pt-1 border-t border-slate-800/60">
                <div className="flex justify-between">
                  <span>72h Rain / Saturation:</span>
                  <strong className="text-slate-300 font-bold">{explanation.rainfall72hMm}mm / {explanation.soilSaturationPct}%</strong>
                </div>
                <div className="flex justify-between">
                  <span>Exposed Population:</span>
                  <strong className="text-slate-300 font-bold">{v.population.toLocaleString()} ({v.vulnerablePop} vuln)</strong>
                </div>
              </div>

              <div className="flex items-center justify-between text-[10px] text-orange-400 font-bold pt-1">
                <span>VIEW DOSSIER & ROUTES →</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
