import React from 'react';

interface SkeletonProps {
  className?: string;
  variant?: 'rectangular' | 'circular' | 'text';
}

export const Skeleton: React.FC<SkeletonProps> = ({
  className = '',
  variant = 'rectangular',
}) => {
  const variantClasses = {
    rectangular: 'rounded-lg',
    circular: 'rounded-full',
    text: 'rounded h-4',
  }[variant];

  return (
    <div
      aria-hidden="true"
      className={`animate-pulse bg-slate-200 dark:bg-slate-800 ${variantClasses} ${className}`}
    />
  );
};

export const CardSkeleton: React.FC<{ rows?: number }> = ({ rows = 3 }) => {
  return (
    <div className="p-4 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3">
      <div className="flex items-center gap-3">
        <Skeleton variant="circular" className="w-10 h-10 shrink-0" />
        <div className="space-y-1.5 flex-1">
          <Skeleton className="w-3/4 h-4" />
          <Skeleton className="w-1/2 h-3" />
        </div>
      </div>
      <div className="space-y-2 pt-2">
        {Array.from({ length: rows }).map((_, i) => (
          <Skeleton key={i} className="w-full h-3" />
        ))}
      </div>
    </div>
  );
};

export const TableRowSkeleton: React.FC<{ columns?: number }> = ({ columns = 4 }) => {
  return (
    <div className="flex items-center gap-4 p-3 border-b border-slate-200 dark:border-slate-800">
      {Array.from({ length: columns }).map((_, i) => (
        <Skeleton key={i} className="flex-1 h-4" />
      ))}
    </div>
  );
};
