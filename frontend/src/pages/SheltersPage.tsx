import React from 'react';
import { useEmergency } from '../context/EmergencyContext';
import { ShelterList } from '../components/evacuation/ShelterList';
import { Building2 } from 'lucide-react';

export const SheltersPage: React.FC = () => {
  const { shelters } = useEmergency();

  const totalCap = shelters.reduce((s, sh) => s + sh.capacity, 0);
  const totalOccupied = shelters.reduce((s, sh) => s + sh.currentOccupancy, 0);
  const remaining = totalCap - totalOccupied;

  return (
    <div className="flex-1 p-4 md:p-6 bg-slate-950 overflow-y-auto font-mono text-xs select-none space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 font-mono">HIGH-GROUND REFUGE SHELTERS</h2>
          <p className="text-xs text-slate-400">
            Designated safe community halls, schools, and campuses with medical and food support
          </p>
        </div>

        <div className="flex items-center gap-2 text-right">
          <div className="p-2 rounded-lg bg-slate-900 border border-slate-800">
            <span className="text-[10px] text-slate-400 block">TOTAL REFUGE CAPACITY</span>
            <strong className="text-sm font-bold text-slate-100">{totalOccupied} / {totalCap} ({remaining} remaining)</strong>
          </div>
        </div>
      </div>

      <ShelterList shelters={shelters} />
    </div>
  );
};
