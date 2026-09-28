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
      bg: 'bg-emerald-950/80 border-emerald-500/40 text-emerald-400',
      dot: 'bg-emerald-400',
      icon: ShieldCheck,
    },
    WATCH: {
      label: 'ADVISORY WATCH',
      bg: 'bg-amber-950/80 border-amber-500/40 text-amber-400',
      dot: 'bg-amber-400 animate-pulse',
      icon: BellRing,
    },
    WARNING: {
      label: 'WARNING: PREPARE',
      bg: 'bg-orange-950/90 border-orange-500/50 text-orange-400',
      dot: 'bg-orange-400 animate-pulse-fast',
      icon: AlertTriangle,
    },
    EVACUATE: {
      label: 'EVACUATE NOW',
      bg: 'bg-red-950/90 border-red-500/60 text-red-300 font-black shadow-lg shadow-red-950/50',
      dot: 'bg-red-500 animate-ping',
      icon: AlertOctagon,
    },
  }[tier] || {
    label: 'UNKNOWN',
    bg: 'bg-slate-800 border-slate-700 text-slate-300',
    dot: 'bg-slate-400',
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
