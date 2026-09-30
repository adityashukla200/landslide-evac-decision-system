import React from 'react';
import { LucideIcon, Inbox, AlertTriangle, RefreshCw } from 'lucide-react';

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description: string;
  actionText?: string;
  onAction?: () => void;
  type?: 'empty' | 'error' | 'offline';
  className?: string;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  icon: Icon = Inbox,
  title,
  description,
  actionText,
  onAction,
  type = 'empty',
  className = '',
}) => {
  const iconColors = {
    empty: 'text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-800/60 border-slate-200 dark:border-slate-700',
    error: 'text-red-500 bg-red-50 dark:bg-red-950/60 border-red-200 dark:border-red-800/60',
    offline: 'text-amber-500 bg-amber-50 dark:bg-amber-950/60 border-amber-200 dark:border-amber-800/60',
  }[type];

  return (
    <div
      className={`flex flex-col items-center justify-center p-8 text-center rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 bg-white/50 dark:bg-slate-900/40 space-y-3 ${className}`}
      role="status"
    >
      <div className={`w-14 h-14 rounded-2xl border flex items-center justify-center shadow-sm ${iconColors}`}>
        <Icon className="w-7 h-7" />
      </div>

      <div className="max-w-md space-y-1">
        <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200 font-mono">
          {title}
        </h3>
        <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed font-sans">
          {description}
        </p>
      </div>

      {actionText && onAction && (
        <button
          onClick={onAction}
          className="mt-2 flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700 text-slate-700 dark:text-slate-200 text-xs font-bold font-mono transition-colors shadow-sm focus-visible:ring-2 focus-visible:ring-orange-500"
        >
          <RefreshCw className="w-3.5 h-3.5" />
          <span>{actionText}</span>
        </button>
      )}
    </div>
  );
};
