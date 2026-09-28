import React from 'react';
import { Shelter } from '../../types';
import { Building2, Phone, Zap, HeartPulse, Droplet, Utensils } from 'lucide-react';

interface ShelterListProps {
  shelters: Shelter[];
}

export const ShelterList: React.FC<ShelterListProps> = ({ shelters }) => {
  return (
    <div className="space-y-3 font-mono text-xs select-none">
      {shelters.map((shelter) => {
        const occupancyPct = Math.round((shelter.currentOccupancy / shelter.capacity) * 100);
        const isFull = occupancyPct >= 90;

        return (
          <div
            key={shelter.id}
            className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 shadow-md space-y-2.5"
          >
            {/* Header */}
            <div className="flex items-start justify-between gap-2 border-b border-slate-800 pb-2">
              <div className="flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-lg bg-blue-950/80 border border-blue-600/50 flex items-center justify-center text-blue-400">
                  <Building2 className="w-4 h-4" />
                </div>
                <div>
                  <h4 className="font-bold text-slate-100 text-xs">{shelter.name}</h4>
                  <div className="text-[10px] text-slate-400">Distance: {shelter.distanceKm} km from ward center</div>
                </div>
              </div>

              <span
                className={`px-2 py-0.5 rounded text-[10px] font-bold border ${
                  isFull
                    ? 'bg-red-950 text-red-300 border-red-800'
                    : 'bg-emerald-950 text-emerald-300 border-emerald-800'
                }`}
              >
                {isFull ? 'NEAR CAPACITY' : 'CAPACITY AVAILABLE'}
              </span>
            </div>

            {/* Occupancy Bar */}
            <div>
              <div className="flex items-center justify-between text-[11px] mb-1 text-slate-300">
                <span>Occupancy: {shelter.currentOccupancy} / {shelter.capacity} people</span>
                <strong className={isFull ? 'text-red-400' : 'text-emerald-400'}>{occupancyPct}%</strong>
              </div>
              <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-800">
                <div
                  className={`h-full rounded-full transition-all ${
                    isFull ? 'bg-red-500' : occupancyPct > 60 ? 'bg-orange-500' : 'bg-emerald-500'
                  }`}
                  style={{ width: `${occupancyPct}%` }}
                />
              </div>
            </div>

            {/* Amenities Grid */}
            <div className="flex flex-wrap items-center justify-between gap-2 pt-2 border-t border-slate-800/80 text-[10px] text-slate-400">
              <div className="flex items-center gap-3">
                <span className={`flex items-center gap-1 ${shelter.amenities.medical ? 'text-emerald-400' : 'text-slate-600'}`}>
                  <HeartPulse className="w-3 h-3" /> Med Aid
                </span>
                <span className={`flex items-center gap-1 ${shelter.amenities.water ? 'text-cyan-400' : 'text-slate-600'}`}>
                  <Droplet className="w-3 h-3" /> Potable Water
                </span>
                <span className={`flex items-center gap-1 ${shelter.amenities.food ? 'text-amber-400' : 'text-slate-600'}`}>
                  <Utensils className="w-3 h-3" /> Rations
                </span>
                <span className={`flex items-center gap-1 ${shelter.amenities.backupPower ? 'text-yellow-400' : 'text-slate-600'}`}>
                  <Zap className="w-3 h-3" /> Genset Power
                </span>
              </div>

              <div className="flex items-center gap-1 text-slate-300">
                <Phone className="w-3 h-3 text-orange-400" />
                <span>{shelter.contactPerson} ({shelter.contactPhone})</span>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
};
