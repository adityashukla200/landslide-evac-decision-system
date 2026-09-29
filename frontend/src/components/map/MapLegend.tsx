import React, { useState } from 'react';
import { Info, X } from 'lucide-react';

export const MapLegend: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-950/95 hover:bg-slate-900 border border-slate-800 text-slate-200 hover:text-white text-xs font-mono shadow-2xl backdrop-blur transition-all active:scale-95"
        title="Open Map Legend"
      >
        <Info className="w-4 h-4 text-orange-400" />
        <span className="font-bold">Legend</span>
      </button>
    );
  }

  return (
    <div className="bg-slate-950/95 border border-slate-800 rounded-lg p-3 text-xs font-mono shadow-2xl backdrop-blur select-none max-w-xs">
      <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2 text-slate-300 font-bold">
        <div className="text-[10px] text-slate-400 uppercase tracking-wider font-bold">
          Operational Map Legend
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Minimize Legend"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      <div className="space-y-1.5">
        {/* Risk Tiers */}
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-red-600 ring-2 ring-red-400/30" />
          <span className="text-slate-300">EVACUATE (Imminent Life Threat)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-orange-500 ring-2 ring-orange-400/30" />
          <span className="text-slate-300">WARNING (Prepare Evacuation)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-amber-400 ring-2 ring-amber-400/30" />
          <span className="text-slate-300">WATCH (Advisory / Monitor)</span>
        </div>
        <div className="flex items-center gap-2">
          <span className="w-3 h-3 rounded-full bg-emerald-500 ring-2 ring-emerald-400/30" />
          <span className="text-slate-300">SAFE / NORMAL (Stable)</span>
        </div>

        <div className="border-t border-slate-800 my-1.5 pt-1.5 space-y-1.5">
          {/* Infrastructure */}
          <div className="flex items-center gap-2">
            <span className="w-4 h-1 rounded bg-emerald-400" />
            <span className="text-slate-300">Recommended Evacuation Trail</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-4 h-1 rounded bg-red-500 border border-dashed border-red-300" />
            <span className="text-slate-300">Severed / Blocked Chute</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-3 h-3 rounded bg-blue-500 flex items-center justify-center text-[9px] text-white font-bold">
              S
            </span>
            <span className="text-slate-300">High-Ground Refuge Shelter</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-400 ring-1 ring-amber-200" />
            <span className="text-slate-300">Telemetry Sensor Station</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 ring-2 ring-rose-300" />
            <span className="text-slate-300">Ground-Truth: Flood Reported</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 ring-2 ring-emerald-200" />
            <span className="text-slate-300">Ground-Truth: False Alarm / Safe</span>
          </div>
        </div>
      </div>
    </div>
  );
};
