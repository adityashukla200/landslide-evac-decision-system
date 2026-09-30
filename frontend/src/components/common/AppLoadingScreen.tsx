import React from 'react';
import { ShieldAlert } from 'lucide-react';

interface AppLoadingScreenProps {
  message?: string;
}

export const AppLoadingScreen: React.FC<AppLoadingScreenProps> = ({
  message = 'Initializing Early Warning Operations...',
}) => {
  return (
    <div
      className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 p-4 transition-colors"
      role="status"
      aria-live="polite"
    >
      <div className="flex flex-col items-center max-w-sm text-center space-y-4">
        {/* Animated Brand Emblem */}
        <div className="relative">
          <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-red-600 via-orange-600 to-amber-600 flex items-center justify-center shadow-2xl shadow-orange-600/30 text-white animate-pulse">
            <ShieldAlert className="w-9 h-9" />
          </div>
          <div className="absolute -inset-2 rounded-3xl border border-orange-500/30 animate-spin duration-1000 pointer-events-none" />
        </div>

        {/* Brand Title */}
        <div className="space-y-1">
          <h2 className="text-sm font-black font-mono tracking-widest text-slate-900 dark:text-slate-100 uppercase">
            HYPER-LOCAL <span className="text-orange-600 dark:text-orange-500">FLASHFLOOD PREDICTION</span>
          </h2>
          <p className="text-[11px] font-mono text-slate-500 dark:text-slate-400">
            Uttarkashi District Early Warning System
          </p>
        </div>

        {/* Progress Spinner & Message */}
        <div className="flex items-center gap-2 pt-2">
          <span className="w-3.5 h-3.5 border-2 border-orange-600 border-t-transparent rounded-full animate-spin" />
          <span className="text-xs text-slate-600 dark:text-slate-400 font-mono">
            {message}
          </span>
        </div>
      </div>
    </div>
  );
};
