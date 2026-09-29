import React from 'react';
import { useEmergency } from '../../context/EmergencyContext';
import { ScenarioType } from '../../types';
import { PlayCircle, CloudRain, AlertTriangle, Waves, ShieldAlert, CheckCircle2 } from 'lucide-react';

export const ScenarioBar: React.FC = () => {
  const { scenario, setScenario } = useEmergency();

  const scenarios: { id: ScenarioType; label: string; icon: any; color: string; desc: string }[] = [
    {
      id: 'NORMAL',
      label: '1. Normal Day',
      icon: CheckCircle2,
      color: 'hover:border-emerald-500 hover:text-emerald-300',
      desc: 'All 25 villages safe, baseline sensor stream',
    },
    {
      id: 'HEAVY_RAIN',
      label: '2. Heavy Rainfall',
      icon: CloudRain,
      color: 'hover:border-blue-500 hover:text-blue-300',
      desc: 'Upstream gauges surge to 35mm/h, 3 villages in WATCH',
    },
    {
      id: 'LANDSLIDE_WARNING',
      label: '3. Landslide Warning',
      icon: AlertTriangle,
      color: 'hover:border-amber-500 hover:text-amber-300',
      desc: 'Bhatwari & Maneri FOS drops to 1.04, soil saturation 91%',
    },
    {
      id: 'FLASH_FLOOD',
      label: '4. Flash Flood Surge',
      icon: Waves,
      color: 'hover:border-orange-500 hover:text-orange-300',
      desc: 'River gauge +2.4m, Route A blocked, Route B safe',
    },
    {
      id: 'EVACUATION',
      label: '5. Full Evacuation',
      icon: ShieldAlert,
      color: 'hover:border-red-500 hover:text-red-300',
      desc: 'EVACUATE order dispatched via multi-channel fallback ladder',
    },
  ];

  return (
    <div className="bg-slate-900/95 border-b border-slate-800 px-4 py-2 flex flex-wrap items-center justify-between gap-2.5 text-xs font-mono">
      <div className="flex items-center gap-2 text-slate-300 font-bold uppercase tracking-wider">
        <PlayCircle className="w-4 h-4 text-orange-400" />
        <span className="hidden sm:inline text-slate-400 font-normal text-xs">Simulate Disaster Lifecycle:</span>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 overflow-x-auto pb-1 sm:pb-0">
        {scenarios.map((sc) => {
          const isActive = scenario === sc.id;
          const Icon = sc.icon;
          return (
            <button
              key={sc.id}
              onClick={() => setScenario(sc.id)}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md border text-xs transition-all active:scale-95 ${
                isActive
                  ? 'bg-orange-600 border-orange-400 text-white font-bold shadow-md shadow-orange-950'
                  : 'bg-slate-950/80 border-slate-800 text-slate-400 ' + sc.color
              }`}
              title={sc.desc}
            >
              <Icon className="w-3.5 h-3.5" />
              <span>{sc.label}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
};
