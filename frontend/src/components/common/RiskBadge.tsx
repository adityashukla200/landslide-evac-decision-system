import React from 'react';
import { RiskTier } from '../../types';
import { ShieldCheck, AlertTriangle, AlertOctagon, BellRing, MinusCircle } from 'lucide-react';

interface RiskBadgeProps {
  tier: RiskTier;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  className?: string;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({
  tier,
  size = 'md',
  showIcon = true,
  className = '',
}) => {
  const config = {
    NONE: {
      label: 'SAFE / NORMAL',
      bg: 'bg-emerald-100 dark:bg-emerald-950/80 border-emerald-500/60 text-emerald-900 dark:text-emerald-300 font-bold',
      dot: 'bg-emerald-600 dark:bg-emerald-400',
      icon: ShieldCheck,
    },
    WATCH: {
      label: 'ADVISORY WATCH',
      bg: 'bg-amber-100 dark:bg-amber-950/80 border-amber-500/60 text-amber-950 dark:text-amber-300 font-bold',
      dot: 'bg-amber-600 dark:bg-amber-400 animate-pulse',
      icon: BellRing,
    },
    WARNING: {
      label: 'WARNING: PREPARE',
      bg: 'bg-orange-100 dark:bg-orange-950/90 border-orange-500/70 text-orange-950 dark:text-orange-300 font-bold',
      dot: 'bg-orange-600 dark:bg-orange-400 animate-pulse-fast',
      icon: AlertTriangle,
    },
    EVACUATE: {
      label: 'EVACUATE NOW',
      bg: 'bg-red-100 dark:bg-red-950/90 border-red-600 text-red-950 dark:text-red-200 font-black shadow-sm dark:shadow-lg dark:shadow-red-950/50',
      dot: 'bg-red-600 dark:bg-red-500 animate-ping',
      icon: AlertOctagon,
    },
  }[tier] || {
    label: 'UNKNOWN',
    bg: 'bg-slate-200 dark:bg-slate-800 border-slate-400 dark:border-slate-700 text-slate-800 dark:text-slate-300 font-bold',
    dot: 'bg-slate-500 dark:bg-slate-400',
    icon: MinusCircle,
  };

  const sizeClasses = {
    sm: 'text-xs px-2 py-0.5 gap-1.5',
    md: 'text-xs px-2.5 py-1 gap-2',
    lg: 'text-sm px-3.5 py-1.5 gap-2.5 font-bold',
  }[size];

  const Icon = config.icon;

  return (
    <span
      className={`inline-flex items-center rounded-full border tracking-wide font-mono uppercase ${config.bg} ${sizeClasses} ${className}`}
    >
      <span className={`w-2 h-2 rounded-full ${config.dot}`} />
      {showIcon && <Icon className={size === 'lg' ? 'w-4 h-4' : 'w-3.5 h-3.5'} />}
      <span>{config.label}</span>
    </span>
  );
};
