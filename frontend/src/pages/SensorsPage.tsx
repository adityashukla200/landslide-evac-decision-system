import React from 'react';
import { useEmergency } from '../context/EmergencyContext';
import { SensorCard } from '../components/sensors/SensorCard';
import { SensorTrustPanel } from '../components/sensors/SensorTrustPanel';
import { Activity, Radio } from 'lucide-react';

export const SensorsPage: React.FC = () => {
  const { sensors } = useEmergency();

  return (
    <div className="flex-1 p-4 md:p-6 bg-slate-950 overflow-y-auto font-mono text-xs select-none space-y-4">
      {/* Header */}
      <div className="border-b border-slate-800 pb-4">
        <h2 className="text-base font-bold text-slate-100 font-mono">SENSOR TELEMETRY & HARDWARE TRUST</h2>
        <p className="text-xs text-slate-400">
          IoT sensor array telemetry, battery health, signal strength, and multi-source consensus validation
        </p>
      </div>

      {/* Sensor Trust Panel */}
      <SensorTrustPanel />

      {/* Sensors Grid */}
      <div className="space-y-2">
        <div className="flex items-center justify-between pb-1 border-b border-slate-800">
          <div className="flex items-center gap-1.5 text-slate-200 font-bold text-sm">
            <Activity className="w-4 h-4 text-orange-400" />
            <span>ACTIVE IoT SENSOR NODES ({sensors.length})</span>
          </div>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {sensors.map((sensor) => (
            <SensorCard key={sensor.id} sensor={sensor} />
          ))}
        </div>
      </div>
    </div>
  );
};
