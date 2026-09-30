import React, { useState } from 'react';
import { useEmergency } from '../context/EmergencyContext';
import { RiskMap } from '../components/map/RiskMap';
import { VillageDetailPanel } from '../components/risk/VillageDetailPanel';
import { RiskBadge } from '../components/common/RiskBadge';
import { AlertCreationModal } from '../components/alerts/AlertCreationModal';
import { CopilotDrawer } from '../components/copilot/CopilotDrawer';
import { PDNAModal } from '../components/institutional/PDNAModal';
import {
  ShieldAlert,
  AlertTriangle,
  BellRing,
  Activity,
  Users,
  Clock,
  Radio,
  MapPin,
  HelpCircle,
  TrendingUp,
  Bot,
  FileSpreadsheet,
} from 'lucide-react';

export const CommandCenter: React.FC = () => {
  const { villages, routes, shelters, sensors, alerts, selectedVillage, setSelectedVillage } = useEmergency();
  const [isAlertModalOpen, setIsAlertModalOpen] = useState(false);
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [isPDNAOpen, setIsPDNAOpen] = useState(false);


  // Key KPI calculations
  const evacuateVillages = villages.filter((v) => v.risk.tier === 'EVACUATE');
  const warningVillages = villages.filter((v) => v.risk.tier === 'WARNING');
  const watchVillages = villages.filter((v) => v.risk.tier === 'WATCH');

  const totalExposedPop = villages
    .filter((v) => v.risk.tier === 'EVACUATE' || v.risk.tier === 'WARNING')
    .reduce((sum, v) => sum + v.population, 0);

  const avgLeadTime = Math.round(
    villages
      .filter((v) => v.risk.tier !== 'NONE')
      .reduce((sum, v) => sum + v.risk.leadTimeMinutes, 0) /
      Math.max(1, villages.filter((v) => v.risk.tier !== 'NONE').length)
  );

  const healthySensors = sensors.filter((s) => s.status === 'HEALTHY').length;
  const faultSensors = sensors.filter((s) => s.status === 'FAULT' || s.status === 'OFFLINE').length;

  return (
    <div className="flex-1 flex flex-col h-full bg-slate-950 font-mono text-xs overflow-hidden">
      {/* Top Operational KPI Bar */}
      <div className="p-3 bg-slate-950 border-b border-slate-800 grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-2 shrink-0 select-none">
        {/* KPI 1: Evacuate */}
        <div className="p-2 rounded-lg bg-red-950/40 border border-red-800/50">
          <div className="text-[10px] text-red-400 font-bold uppercase tracking-wider flex items-center gap-1">
            <ShieldAlert className="w-3 h-3" /> EVACUATE
          </div>
          <div className="text-xl font-black text-red-200 mt-0.5">{evacuateVillages.length}</div>
          <div className="text-[9px] text-slate-500">Immediate Life Threat</div>
        </div>

        {/* KPI 2: Warning */}
        <div className="p-2 rounded-lg bg-orange-950/40 border border-orange-800/50">
          <div className="text-[10px] text-orange-400 font-bold uppercase tracking-wider flex items-center gap-1">
            <AlertTriangle className="w-3 h-3" /> WARNING
          </div>
          <div className="text-xl font-black text-orange-200 mt-0.5">{warningVillages.length}</div>
          <div className="text-[9px] text-slate-500">Prepare Evacuation</div>
        </div>

        {/* KPI 3: Watch */}
        <div className="p-2 rounded-lg bg-amber-950/40 border border-amber-800/50">
          <div className="text-[10px] text-amber-400 font-bold uppercase tracking-wider flex items-center gap-1">
            <BellRing className="w-3 h-3" /> WATCH
          </div>
          <div className="text-xl font-black text-amber-200 mt-0.5">{watchVillages.length}</div>
          <div className="text-[9px] text-slate-500">Advisory Monitoring</div>
        </div>

        {/* KPI 4: Highest Risk Node */}
        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider">HIGHEST RISK</div>
          <div className="text-xs font-bold text-slate-100 truncate mt-0.5">
            {evacuateVillages[0]?.name || warningVillages[0]?.name || 'All Stable'}
          </div>
          <div className="text-[9px] text-orange-400">
            {evacuateVillages[0] ? `Risk: ${(evacuateVillages[0].risk.probability * 100).toFixed(0)}%` : 'Stable'}
          </div>
        </div>

        {/* KPI 5: Population Exposed */}
        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Users className="w-3 h-3 text-slate-500" /> PEOPLE AT RISK
          </div>
          <div className="text-xl font-black text-slate-100 mt-0.5">{totalExposedPop.toLocaleString()}</div>
          <div className="text-[9px] text-slate-500">In Warning/Evac Wards</div>
        </div>

        {/* KPI 6: Average Lead Time */}
        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Clock className="w-3 h-3 text-orange-400" /> AVG LEAD TIME
          </div>
          <div className="text-xl font-black text-orange-300 mt-0.5">~{avgLeadTime}m</div>
          <div className="text-[9px] text-slate-500">Pre-Failure Window</div>
        </div>

        {/* KPI 7: Sensor Health */}
        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Activity className="w-3 h-3 text-emerald-400" /> ACTIVE SENSORS
          </div>
          <div className="text-xl font-black text-emerald-400 mt-0.5">{healthySensors}/{sensors.length}</div>
          <div className="text-[9px] text-slate-500">{faultSensors > 0 ? `${faultSensors} Anomaly` : 'All Optimal'}</div>
        </div>

        {/* KPI 8: Active Directives */}
        <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
          <div className="text-[10px] text-slate-400 uppercase tracking-wider flex items-center gap-1">
            <Radio className="w-3 h-3 text-red-400" /> DIRECTIVES
          </div>
          <div className="text-xl font-black text-slate-100 mt-0.5">{alerts.length}</div>
          <div className="text-[9px] text-emerald-400 font-bold">100% Broadcasted</div>
        </div>
      </div>

      {/* Main Command Center Body: GIS Map + Interactive Slideout */}
      <div className="flex-1 flex relative overflow-hidden">
        {/* Primary GIS Map */}
        <div className="flex-1 h-full relative">
          <RiskMap
            villages={villages}
            routes={routes}
            shelters={shelters}
            sensors={sensors}
            selectedVillage={selectedVillage}
            onSelectVillage={(v) => setSelectedVillage(v)}
          />

          {/* Floating Operator Action Suite */}
          <div className="absolute bottom-5 left-5 z-20 flex items-center gap-2">
            <button
              onClick={() => setIsCopilotOpen(true)}
              className="px-3.5 py-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white font-bold shadow-lg shadow-emerald-950/60 flex items-center gap-2 border border-emerald-400/40 transition-all hover:scale-105 select-none"
            >
              <Bot className="w-4 h-4 animate-bounce" />
              <span>AI COPILOT</span>
              <span className="w-2 h-2 rounded-full bg-emerald-300 animate-ping" />
            </button>

            <button
              onClick={() => setIsPDNAOpen(true)}
              className="px-3.5 py-2 rounded-xl bg-slate-900/90 hover:bg-slate-800 text-slate-200 font-bold shadow-lg shadow-black/50 flex items-center gap-2 border border-slate-700 transition-all hover:scale-105 select-none backdrop-blur-md"
            >
              <FileSpreadsheet className="w-4 h-4 text-blue-400" />
              <span>NDMA PDNA</span>
            </button>
          </div>
        </div>

        {/* Slideout Village Detail Dossier */}
        {selectedVillage && (
          <VillageDetailPanel
            village={selectedVillage}
            routes={routes}
            shelters={shelters}
            onClose={() => setSelectedVillage(null)}
            onTriggerAlert={() => setIsAlertModalOpen(true)}
          />
        )}
      </div>

      {/* Alert Dispatch Modal */}
      <AlertCreationModal
        isOpen={isAlertModalOpen}
        onClose={() => setIsAlertModalOpen(false)}
        defaultVillageId={selectedVillage?.id}
        defaultTier={selectedVillage?.risk.tier === 'NONE' ? 'WARNING' : selectedVillage?.risk.tier}
      />

      {/* AI Disaster Copilot Drawer */}
      <CopilotDrawer
        isOpen={isCopilotOpen}
        onClose={() => setIsCopilotOpen(false)}
        onOpenPDNAModal={() => setIsPDNAOpen(true)}
      />

      {/* NDMA PDNA Assessment Modal */}
      <PDNAModal
        isOpen={isPDNAOpen}
        onClose={() => setIsPDNAOpen(false)}
      />
    </div>
  );
};

