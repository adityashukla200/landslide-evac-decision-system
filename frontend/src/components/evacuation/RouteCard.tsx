import React from 'react';
import { Route } from '../../types';
import { Footprints, CheckCircle2, AlertOctagon, Clock, ShieldAlert } from 'lucide-react';

interface RouteCardProps {
  route: Route;
}

export const RouteCard: React.FC<RouteCardProps> = ({ route }) => {
  return (
    <div
      className={`p-3.5 rounded-xl border font-mono text-xs shadow-md transition-all select-none ${
        route.isRecommended
          ? 'bg-emerald-950/20 border-emerald-500/50 shadow-emerald-950/30'
          : route.isBlocked
          ? 'bg-red-950/20 border-red-500/50 opacity-80'
          : 'bg-slate-900 border-slate-800'
      }`}
    >
      <div className="flex items-start justify-between gap-2 border-b border-slate-800/80 pb-2 mb-2">
        <div className="flex items-center gap-2">
          <div
            className={`p-2 rounded-lg border ${
              route.isRecommended
                ? 'bg-emerald-950 text-emerald-400 border-emerald-600'
                : route.isBlocked
                ? 'bg-red-950 text-red-400 border-red-600'
                : 'bg-slate-950 text-slate-400 border-slate-800'
            }`}
          >
            <Footprints className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold text-slate-100 text-xs">{route.name}</div>
            <div className="text-[10px] text-slate-400">ID: {route.id}</div>
          </div>
        </div>

        {route.isRecommended ? (
          <span className="px-2 py-0.5 rounded bg-emerald-950 text-emerald-300 border border-emerald-700 text-[10px] font-bold flex items-center gap-1">
            <CheckCircle2 className="w-3 h-3" />
            <span>RECOMMENDED</span>
          </span>
        ) : route.isBlocked ? (
          <span className="px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-700 text-[10px] font-bold flex items-center gap-1">
            <AlertOctagon className="w-3 h-3" />
            <span>SEVERED / BLOCKED</span>
          </span>
        ) : (
          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 text-[10px]">
            ALTERNATIVE
          </span>
        )}
      </div>

      {/* Metrics Row */}
      <div className="grid grid-cols-3 gap-2 text-[11px] p-2 rounded-lg bg-slate-950/70 border border-slate-800/60 my-2">
        <div>
          <span className="text-[10px] text-slate-500 block">DISTANCE</span>
          <span className="font-bold text-slate-200">{route.lengthKm} km</span>
        </div>
        <div>
          <span className="text-[10px] text-slate-500 block">EST. WALK</span>
          <span className="font-bold text-slate-200 flex items-center gap-1">
            <Clock className="w-3 h-3 text-orange-400" /> ~{route.estWalkMinutes} min
          </span>
        </div>
        <div>
          <span className="text-[10px] text-slate-500 block">CUT RISK</span>
          <span
            className={`font-bold ${
              route.cutRisk > 0.5 ? 'text-red-400' : 'text-emerald-400'
            }`}
          >
            {(route.cutRisk * 100).toFixed(0)}%
          </span>
        </div>
      </div>

      {route.description && (
        <div className="text-[11px] text-slate-300 mt-2 flex items-start gap-1.5 font-sans leading-tight">
          {route.isBlocked ? (
            <ShieldAlert className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
          ) : (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
          )}
          <span>{route.description}</span>
        </div>
      )}
    </div>
  );
};
