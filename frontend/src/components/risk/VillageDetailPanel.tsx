import React from 'react';
import { Village, Route, Shelter } from '../../types';
import { RiskBadge } from '../common/RiskBadge';
import { RiskTimeline } from './RiskTimeline';
import {
  X,
  AlertOctagon,
  Clock,
  Shield,
  Footprints,
  Building2,
  HelpCircle,
  TrendingUp,
  Mountain,
  Droplets,
  CloudRain,
  Compass,
} from 'lucide-react';

interface VillageDetailPanelProps {
  village: Village | null;
  routes: Route[];
  shelters: Shelter[];
  onClose: () => void;
  onTriggerAlert: (villageId: string, tier: any) => void;
}

export const VillageDetailPanel: React.FC<VillageDetailPanelProps> = ({
  village,
  routes,
  shelters,
  onClose,
  onTriggerAlert,
}) => {
  if (!village) return null;

  const { risk, explanation } = { risk: village.risk, explanation: village.risk.explanation };

  const villageRoutes = routes.filter((r) => r.fromVillageId === village.id);
  const recommendedRoute = villageRoutes.find((r) => r.isRecommended) || villageRoutes[0];
  const targetShelter = shelters.find((s) => s.id === recommendedRoute?.toShelterId) || shelters[0];

  // Factor of safety color
  const fosColor =
    explanation.factorOfSafety < 1.0
      ? 'text-red-400 bg-red-950/80 border-red-500/50'
      : explanation.factorOfSafety < 1.2
      ? 'text-orange-400 bg-orange-950/80 border-orange-500/50'
      : 'text-emerald-400 bg-emerald-950/80 border-emerald-500/50';

  return (
    <div className="w-96 md:w-[420px] bg-slate-950 border-l border-slate-800 h-full flex flex-col justify-between shadow-2xl z-30 font-mono text-xs overflow-y-auto select-none">
      {/* Panel Header */}
      <div>
        <div className="p-4 border-b border-slate-800 bg-slate-900/60 sticky top-0 backdrop-blur z-10">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div>
              <span className="text-[10px] text-orange-400 uppercase tracking-widest font-bold block">
                VILLAGE / WARD DOSSIER
              </span>
              <h2 className="text-lg font-black text-slate-100">{village.name}</h2>
              <div className="flex items-center gap-2 text-[11px] text-slate-400 mt-0.5">
                <span>{village.district}</span>
                <span>•</span>
                <span>Elev: {village.elevationM}m</span>
                <span>•</span>
                <span>Pop: {village.population.toLocaleString()} ({village.vulnerablePop} vuln)</span>
              </div>
            </div>
            <button
              onClick={onClose}
              className="p-1 rounded bg-slate-800 text-slate-400 hover:text-white transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex items-center justify-between gap-2 mt-2">
            <RiskBadge tier={risk.tier} size="md" />
            <div className="flex items-center gap-1.5 text-red-400 font-bold bg-red-950/80 px-2.5 py-1 rounded border border-red-500/40">
              <Clock className="w-3.5 h-3.5 animate-pulse" />
              <span>LEAD TIME: ~{risk.leadTimeMinutes} MIN</span>
            </div>
          </div>
        </div>

        {/* Core Risk Metrics Grid */}
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-2 gap-2.5">
            {/* Calibrated Probability */}
            <div className="p-2.5 rounded-lg bg-slate-900 border border-slate-800">
              <div className="flex items-center justify-between text-slate-400 text-[10px] mb-1">
                <span>CALIBRATED RISK</span>
                <TrendingUp className="w-3.5 h-3.5 text-orange-400" />
              </div>
              <div className="text-xl font-black text-slate-100">
                {(risk.probability * 100).toFixed(0)}%
              </div>
              <div className="text-[10px] text-slate-500 mt-0.5">
                Uncertainty: [{(risk.lowerBound * 100).toFixed(0)}% – {(risk.upperBound * 100).toFixed(0)}%]
              </div>
            </div>

            {/* Factor of Safety (FOS) */}
            <div className={`p-2.5 rounded-lg border ${fosColor}`}>
              <div className="flex items-center justify-between text-[10px] mb-1 opacity-80">
                <span>FACTOR OF SAFETY</span>
                <Mountain className="w-3.5 h-3.5" />
              </div>
              <div className="text-xl font-black">
                {explanation.factorOfSafety.toFixed(2)}
              </div>
              <div className="text-[10px] mt-0.5">
                {explanation.factorOfSafety < 1.0 ? 'CRITICAL FAILURE' : 'STABLE SLOPE'}
              </div>
            </div>
          </div>

          {/* "WHY THIS ALERT FIRED" Explainability Section */}
          <div className="p-3 rounded-lg bg-slate-900/90 border border-slate-800">
            <div className="flex items-center gap-1.5 text-slate-200 font-bold mb-2 pb-1 border-b border-slate-800">
              <HelpCircle className="w-4 h-4 text-orange-400" />
              <span>WHY THIS RISK INCREASED</span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-slate-300 text-[11px]">
              <div className="flex items-center gap-2 p-1.5 rounded bg-slate-950/60 border border-slate-800">
                <CloudRain className="w-3.5 h-3.5 text-blue-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500">72h Rainfall</div>
                  <div className="font-bold text-slate-200">{explanation.rainfall72hMm} mm</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-1.5 rounded bg-slate-950/60 border border-slate-800">
                <Droplets className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500">Soil Saturation</div>
                  <div className="font-bold text-slate-200">{explanation.soilSaturationPct}%</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-1.5 rounded bg-slate-950/60 border border-slate-800">
                <Compass className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500">Terrain Slope</div>
                  <div className="font-bold text-slate-200">{explanation.slopeDeg}° (Steep)</div>
                </div>
              </div>

              <div className="flex items-center gap-2 p-1.5 rounded bg-slate-950/60 border border-slate-800">
                <CloudRain className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <div>
                  <div className="text-[10px] text-slate-500">Nowcast Rate</div>
                  <div className="font-bold text-slate-200">{explanation.currentRainfallRateMmH} mm/h</div>
                </div>
              </div>
            </div>

            {/* Analog Event Pattern Match */}
            {explanation.analogMatch && (
              <div className="mt-2.5 p-2 rounded bg-orange-950/40 border border-orange-700/40 text-[11px]">
                <div className="flex items-center justify-between font-bold text-orange-300 mb-0.5">
                  <span>HISTORICAL ANALOG MATCH</span>
                  <span>{explanation.analogMatch.similarityPct}% MATCH</span>
                </div>
                <div className="text-slate-300 font-semibold">{explanation.analogMatch.eventName}</div>
                <div className="text-[10px] text-slate-400 mt-0.5">{explanation.analogMatch.description}</div>
              </div>
            )}
          </div>

          {/* Risk Timeline Observed vs Predicted */}
          <RiskTimeline risk={risk} height={150} />

          {/* Evacuation Route & Shelter Summary */}
          <div className="p-3 rounded-lg bg-slate-900 border border-slate-800 space-y-2">
            <div className="flex items-center justify-between text-slate-200 font-bold border-b border-slate-800 pb-1">
              <div className="flex items-center gap-1.5">
                <Footprints className="w-4 h-4 text-emerald-400" />
                <span>RECOMMENDED EVACUATION ROUTE</span>
              </div>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-emerald-950 text-emerald-400 border border-emerald-800">
                CLEAR
              </span>
            </div>

            {recommendedRoute ? (
              <div>
                <div className="font-bold text-slate-200 text-[11px]">{recommendedRoute.name}</div>
                <div className="text-[10px] text-slate-400">
                  Distance: {recommendedRoute.lengthKm} km • Walk Time: ~{recommendedRoute.estWalkMinutes} min • Severance Risk: {(recommendedRoute.cutRisk * 100).toFixed(0)}%
                </div>
                {recommendedRoute.description && (
                  <div className="text-[10px] text-emerald-400/90 mt-1">{recommendedRoute.description}</div>
                )}
              </div>
            ) : (
              <div className="text-slate-400 text-[10px]">No route mapped</div>
            )}

            {targetShelter && (
              <div className="pt-2 border-t border-slate-800 flex items-center justify-between text-[11px]">
                <div className="flex items-center gap-1.5 text-slate-300">
                  <Building2 className="w-3.5 h-3.5 text-blue-400" />
                  <span className="truncate max-w-[200px]">{targetShelter.name}</span>
                </div>
                <span className="text-slate-400 text-[10px]">
                  Cap: {targetShelter.currentOccupancy}/{targetShelter.capacity}
                </span>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Action Footer */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/90 sticky bottom-0">
        <button
          onClick={() => onTriggerAlert(village.id, 'EVACUATE')}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-black tracking-wider transition-colors shadow-lg shadow-red-950 border border-red-400/40 active:scale-98"
        >
          <AlertOctagon className="w-4 h-4" />
          <span>ISSUE EVACUATION DIRECTIVE</span>
        </button>
      </div>
    </div>
  );
};
