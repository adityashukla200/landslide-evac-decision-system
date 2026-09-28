import React from 'react';
import { useEmergency } from '../context/EmergencyContext';
import { RiskMap } from '../components/map/RiskMap';
import { VillageDetailPanel } from '../components/risk/VillageDetailPanel';

export const LiveRiskMapPage: React.FC = () => {
  const { villages, routes, shelters, sensors, selectedVillage, setSelectedVillage } = useEmergency();

  return (
    <div className="flex-1 flex h-full bg-slate-950 relative overflow-hidden font-mono text-xs">
      <div className="flex-1 h-full relative">
        <RiskMap
          villages={villages}
          routes={routes}
          shelters={shelters}
          sensors={sensors}
          selectedVillage={selectedVillage}
          onSelectVillage={(v) => setSelectedVillage(v)}
        />
      </div>

      {selectedVillage && (
        <VillageDetailPanel
          village={selectedVillage}
          routes={routes}
          shelters={shelters}
          onClose={() => setSelectedVillage(null)}
          onTriggerAlert={() => {}}
        />
      )}
    </div>
  );
};
