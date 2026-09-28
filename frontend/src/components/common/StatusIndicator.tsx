import React from 'react';
import { Wifi, WifiOff, Activity, ShieldAlert } from 'lucide-react';

interface StatusIndicatorProps {
  isOnline: boolean;
  activeIncidentsCount?: number;
  className?: string;
}

export const StatusIndicator: React.FC<StatusIndicatorProps> = ({
  isOnline,
  activeIncidentsCount = 0,
  className = '',
}) => {
  return (
    <div className={`flex items-center gap-3 font-mono text-xs ${className}`}>
      {/* Connectivity Status */}
      <div
        className={`flex items-center gap-1.5 px-2.5 py-1 rounded border ${
          isOnline
            ? 'bg-slate-900/90 border-emerald-500/30 text-emerald-400'
            : 'bg-amber-950/90 border-amber-500/50 text-amber-300'
        }`}
      >
        {isOnline ? (
          <>
            <Wifi className="w-3.5 h-3.5 text-emerald-400" />
            <span className="hidden sm:inline">SYSTEM OPERATIONAL</span>
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
          </>
        ) : (
          <>
            <WifiOff className="w-3.5 h-3.5 text-amber-400" />
            <span>OFFLINE (CACHED DATA)</span>
            <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
          </>
        )}
      </div>

      {/* Incident Pill */}
      {activeIncidentsCount > 0 ? (
        <div className="flex items-center gap-1.5 px-2.5 py-1 rounded border bg-red-950/90 border-red-500/50 text-red-300 font-bold animate-pulse">
          <ShieldAlert className="w-3.5 h-3.5 text-red-400" />
          <span>{activeIncidentsCount} ACTIVE DIRECTIVES</span>
        </div>
      ) : (
        <div className="hidden md:flex items-center gap-1.5 px-2 py-1 rounded border bg-slate-900/60 border-slate-700 text-slate-400">
          <Activity className="w-3 h-3 text-slate-500" />
          <span>ZERO THREAT DIRECTIVES</span>
        </div>
      )}
    </div>
  );
};
