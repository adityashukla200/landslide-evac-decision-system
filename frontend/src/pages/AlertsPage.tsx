import React, { useState } from 'react';
import { useEmergency } from '../context/EmergencyContext';
import { AlertCard } from '../components/alerts/AlertCard';
import { AlertCreationModal } from '../components/alerts/AlertCreationModal';
import { BellRing, Plus, Radio, ShieldAlert, CheckCircle2, Inbox } from 'lucide-react';
import { EmptyState } from '../components/common/EmptyState';

export const AlertsPage: React.FC = () => {
  const { alerts } = useEmergency();
  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [filterTier, setFilterTier] = useState<string>('ALL');

  const filtered = alerts.filter((a) => filterTier === 'ALL' || a.tier === filterTier);

  return (
    <div className="flex-1 p-4 md:p-6 bg-slate-50 dark:bg-slate-950 overflow-y-auto font-mono text-xs select-none space-y-4 transition-colors">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 dark:border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-bold text-slate-900 dark:text-slate-100 font-mono">ALERT MANAGEMENT CENTER</h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Multi-channel emergency broadcast directives, fallback delivery ladders, and acknowledgement tracking
          </p>
        </div>

        <div className="flex items-center gap-2">
          {/* Tier Filter */}
          <select
            value={filterTier}
            onChange={(e) => setFilterTier(e.target.value)}
            className="bg-white dark:bg-slate-900 text-xs text-slate-800 dark:text-slate-300 px-3 py-1.5 rounded-lg border border-slate-300 dark:border-slate-800 outline-none cursor-pointer focus-visible:ring-2 focus-visible:ring-orange-500"
          >
            <option value="ALL">All Directives ({alerts.length})</option>
            <option value="EVACUATE">EVACUATE ({alerts.filter((a) => a.tier === 'EVACUATE').length})</option>
            <option value="WARNING">WARNING ({alerts.filter((a) => a.tier === 'WARNING').length})</option>
            <option value="WATCH">WATCH ({alerts.filter((a) => a.tier === 'WATCH').length})</option>
          </select>

          {/* Create Alert Button */}
          <button
            onClick={() => setIsCreateModalOpen(true)}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-red-600 hover:bg-red-500 text-white font-bold text-xs tracking-wider transition-colors shadow-lg shadow-red-950/20 dark:shadow-red-950 border border-red-400/40"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>CREATE NEW DIRECTIVE</span>
          </button>
        </div>
      </div>

      {/* Alert Cards List or Empty State */}
      {filtered.length === 0 ? (
        <EmptyState
          icon={Inbox}
          title="No Active Emergency Alerts"
          description={
            filterTier === 'ALL'
              ? 'No active alerts have been dispatched in Uttarkashi district. All river catchments and slopes are within normal advisory parameters.'
              : `No active ${filterTier} tier directives are currently active.`
          }
          actionText={filterTier !== 'ALL' ? 'Show All Directives' : 'Dispatch Directive'}
          onAction={() => {
            if (filterTier !== 'ALL') setFilterTier('ALL');
            else setIsCreateModalOpen(true);
          }}
        />
      ) : (
        <div className="space-y-3">
          {filtered.map((alert) => (
            <AlertCard key={alert.id} alert={alert} />
          ))}
        </div>
      )}

      {/* Alert Creation Modal */}
      <AlertCreationModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
      />
    </div>
  );
};
