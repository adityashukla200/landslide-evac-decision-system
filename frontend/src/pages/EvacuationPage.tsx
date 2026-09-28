import React from 'react';
import { useEmergency } from '../context/EmergencyContext';
import { RouteCard } from '../components/evacuation/RouteCard';
import { ShelterList } from '../components/evacuation/ShelterList';
import { Footprints, Building2, ShieldAlert, CheckCircle2 } from 'lucide-react';

export const EvacuationPage: React.FC = () => {
  const { routes, shelters } = useEmergency();

  return (
    <div className="flex-1 p-4 md:p-6 bg-slate-950 overflow-y-auto font-mono text-xs select-none space-y-4">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-base font-bold text-slate-100 font-mono">EVACUATION ROUTING & SHELTER LOGISTICS</h2>
        <p className="text-xs text-slate-400">
          NetworkX dynamic trail analysis, terrain cut-risk avoidance, and high-ground refuge capacities
        </p>
      </div>

      {/* Two Column Layout: Routes vs Shelters */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Left: Evacuation Routes */}
        <div className="space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-1.5 text-slate-200 font-bold text-sm">
              <Footprints className="w-4 h-4 text-emerald-400" />
              <span>EVACUATION TRAILS & ROAD SEGMENTS</span>
            </div>
            <span className="text-[10px] text-slate-500">{routes.length} Monitored Trails</span>
          </div>

          <div className="space-y-2.5">
            {routes.map((route) => (
              <RouteCard key={route.id} route={route} />
            ))}
          </div>
        </div>

        {/* Right: Shelters */}
        <div className="space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-slate-800">
            <div className="flex items-center gap-1.5 text-slate-200 font-bold text-sm">
              <Building2 className="w-4 h-4 text-blue-400" />
              <span>DESIGNATED REFUGE SHELTERS</span>
            </div>
            <span className="text-[10px] text-slate-500">{shelters.length} Facilities</span>
          </div>

          <ShelterList shelters={shelters} />
        </div>
      </div>
    </div>
  );
};
