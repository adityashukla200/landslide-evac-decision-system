import React from 'react';
import { useEmergency } from '../../context/EmergencyContext';
import { Sliders, RotateCcw, AlertOctagon, Users, Footprints, ShieldCheck } from 'lucide-react';
import { RiskBadge } from '../common/RiskBadge';

export const WhatIfSimulator: React.FC = () => {
  const { simulationParams, setSimulationParams, villages, simulatedVillages } = useEmergency();

  const handleReset = () => {
    setSimulationParams({
      rainfallIncreasePct: 0,
      soilSaturationIncreasePct: 0,
      upstreamInflowIncreasePct: 0,
    });
  };

  const baseEvac = villages.filter((v) => v.risk.tier === 'EVACUATE').length;
  const baseWarn = villages.filter((v) => v.risk.tier === 'WARNING').length;
  const baseExposed = villages
    .filter((v) => v.risk.tier === 'EVACUATE' || v.risk.tier === 'WARNING')
    .reduce((sum, v) => sum + v.population, 0);

  const simEvac = simulatedVillages.filter((v) => v.risk.tier === 'EVACUATE').length;
  const simWarn = simulatedVillages.filter((v) => v.risk.tier === 'WARNING').length;
  const simExposed = simulatedVillages
    .filter((v) => v.risk.tier === 'EVACUATE' || v.risk.tier === 'WARNING')
    .reduce((sum, v) => sum + v.population, 0);

  const isSimulated =
    simulationParams.rainfallIncreasePct !== 0 ||
    simulationParams.soilSaturationIncreasePct !== 0 ||
    simulationParams.upstreamInflowIncreasePct !== 0;

  return (
    <div className="space-y-4 font-mono text-xs select-none">
      {/* Simulation Banner */}
      <div className="p-3.5 rounded-xl bg-orange-950/40 border border-orange-700/50 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-orange-600 flex items-center justify-center text-white">
            <Sliders className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold text-slate-100 text-sm">Disaster Scenario "What-If" Modeler</div>
            <div className="text-[11px] text-slate-400">
              Perturb environmental boundary conditions and model dynamic catchment cascading response
            </div>
          </div>
        </div>

        {isSimulated && (
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs transition-colors border border-slate-700"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>RESET TO BASELINE</span>
          </button>
        )}
      </div>

      {/* Sliders Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3 p-4 rounded-xl bg-slate-900 border border-slate-800">
        {/* Rainfall Intensity Slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-[11px]">
            <span className="text-slate-400">Rainfall Intensity</span>
            <strong className="text-blue-400 font-bold">
              {simulationParams.rainfallIncreasePct > 0 ? `+${simulationParams.rainfallIncreasePct}%` : `${simulationParams.rainfallIncreasePct}%`}
            </strong>
          </div>
          <input
            type="range"
            min="-30"
            max="100"
            step="5"
            value={simulationParams.rainfallIncreasePct}
            onChange={(e) =>
              setSimulationParams((prev) => ({ ...prev, rainfallIncreasePct: Number(e.target.value) }))
            }
            className="w-full accent-blue-500 cursor-pointer"
          />
          <div className="flex justify-between text-[9px] text-slate-500">
            <span>-30%</span>
            <span>0% (Observed)</span>
            <span>+100% Cloudburst</span>
          </div>
        </div>

        {/* Soil Saturation Slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-[11px]">
            <span className="text-slate-400">Antecedent Soil Saturation</span>
            <strong className="text-cyan-400 font-bold">
              {simulationParams.soilSaturationIncreasePct > 0
                ? `+${simulationParams.soilSaturationIncreasePct}%`
                : `${simulationParams.soilSaturationIncreasePct}%`}
            </strong>
          </div>
          <input
            type="range"
            min="-20"
            max="50"
            step="5"
            value={simulationParams.soilSaturationIncreasePct}
            onChange={(e) =>
              setSimulationParams((prev) => ({ ...prev, soilSaturationIncreasePct: Number(e.target.value) }))
            }
            className="w-full accent-cyan-500 cursor-pointer"
          />
          <div className="flex justify-between text-[9px] text-slate-500">
            <span>-20%</span>
            <span>0% (Observed)</span>
            <span>+50% Saturated</span>
          </div>
        </div>

        {/* Upstream Inflow Slider */}
        <div className="space-y-1.5">
          <div className="flex justify-between text-[11px]">
            <span className="text-slate-400">Upstream River Inflow Surge</span>
            <strong className="text-orange-400 font-bold">
              {simulationParams.upstreamInflowIncreasePct > 0
                ? `+${simulationParams.upstreamInflowIncreasePct}%`
                : `${simulationParams.upstreamInflowIncreasePct}%`}
            </strong>
          </div>
          <input
            type="range"
            min="-20"
            max="100"
            step="5"
            value={simulationParams.upstreamInflowIncreasePct}
            onChange={(e) =>
              setSimulationParams((prev) => ({ ...prev, upstreamInflowIncreasePct: Number(e.target.value) }))
            }
            className="w-full accent-orange-500 cursor-pointer"
          />
          <div className="flex justify-between text-[9px] text-slate-500">
            <span>-20%</span>
            <span>0% (Observed)</span>
            <span>+100% Dam Overflow</span>
          </div>
        </div>
      </div>

      {/* Comparative Impact Cards (Baseline vs Simulation) */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        {/* Baseline State */}
        <div className="p-3.5 rounded-xl bg-slate-900/60 border border-slate-800 space-y-2">
          <div className="text-[10px] text-slate-500 uppercase tracking-wider font-bold">
            Baseline Observed State
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="p-2 rounded bg-slate-950 border border-slate-800">
              <span className="text-[10px] text-slate-400 block">EVACUATE</span>
              <strong className="text-lg text-red-400 font-black">{baseEvac}</strong>
            </div>
            <div className="p-2 rounded bg-slate-950 border border-slate-800">
              <span className="text-[10px] text-slate-400 block">WARNING</span>
              <strong className="text-lg text-orange-400 font-black">{baseWarn}</strong>
            </div>
            <div className="p-2 rounded bg-slate-950 border border-slate-800">
              <span className="text-[10px] text-slate-400 block">POPULATION</span>
              <strong className="text-lg text-slate-200 font-black">{baseExposed.toLocaleString()}</strong>
            </div>
          </div>
        </div>

        {/* Simulated State */}
        <div className="p-3.5 rounded-xl bg-orange-950/20 border border-orange-600/40 space-y-2 shadow-lg">
          <div className="flex items-center justify-between text-[10px] uppercase tracking-wider font-bold text-orange-400">
            <span>Simulated Stress Outcome</span>
            {isSimulated && <span className="animate-pulse">SIMULATION ACTIVE</span>}
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            <div className="p-2 rounded bg-slate-950 border border-red-800/40">
              <span className="text-[10px] text-slate-400 block">EVACUATE</span>
              <strong className="text-lg text-red-400 font-black">{simEvac}</strong>
              {simEvac > baseEvac && (
                <span className="text-[9px] text-red-300 font-bold block">+{simEvac - baseEvac} wards</span>
              )}
            </div>
            <div className="p-2 rounded bg-slate-950 border border-orange-800/40">
              <span className="text-[10px] text-slate-400 block">WARNING</span>
              <strong className="text-lg text-orange-400 font-black">{simWarn}</strong>
              {simWarn > baseWarn && (
                <span className="text-[9px] text-orange-300 font-bold block">+{simWarn - baseWarn} wards</span>
              )}
            </div>
            <div className="p-2 rounded bg-slate-950 border border-slate-800">
              <span className="text-[10px] text-slate-400 block">POPULATION</span>
              <strong className="text-lg text-amber-300 font-black">{simExposed.toLocaleString()}</strong>
              {simExposed > baseExposed && (
                <span className="text-[9px] text-amber-400 font-bold block">
                  +{(simExposed - baseExposed).toLocaleString()} at risk
                </span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Simulated Villages Table Breakdown */}
      <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
        <h4 className="font-bold text-slate-200 text-xs border-b border-slate-800 pb-1.5">
          Ward-by-Ward Stress Response Matrix
        </h4>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-[11px]">
            <thead>
              <tr className="text-slate-500 border-b border-slate-800">
                <th className="py-1.5">Village / Ward</th>
                <th>Baseline Tier</th>
                <th>Simulated Tier</th>
                <th>Sim. FOS</th>
                <th>Sim. Probability</th>
                <th>Sim. Lead Time</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {simulatedVillages.map((sv) => {
                const bv = villages.find((v) => v.id === sv.id)!;
                const isEscalated = sv.risk.tier !== bv.risk.tier;

                return (
                  <tr key={sv.id} className={isEscalated ? 'bg-orange-950/20' : ''}>
                    <td className="py-2 font-bold text-slate-200">{sv.name}</td>
                    <td>
                      <RiskBadge tier={bv.risk.tier} size="sm" />
                    </td>
                    <td>
                      <RiskBadge tier={sv.risk.tier} size="sm" />
                    </td>
                    <td
                      className={`font-bold ${
                        sv.risk.explanation.factorOfSafety < 1.0 ? 'text-red-400' : 'text-emerald-400'
                      }`}
                    >
                      {sv.risk.explanation.factorOfSafety.toFixed(2)}
                    </td>
                    <td className="font-bold text-slate-100">{(sv.risk.probability * 100).toFixed(0)}%</td>
                    <td className="text-orange-400 font-bold">~{sv.risk.leadTimeMinutes} min</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
