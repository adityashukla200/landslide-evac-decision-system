import React from 'react';
import { Sensor } from '../../types';
import {
  CloudRain,
  Droplets,
  Waves,
  Compass,
  Battery,
  Signal,
  AlertTriangle,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

interface SensorCardProps {
  sensor: Sensor;
}

export const SensorCard: React.FC<SensorCardProps> = ({ sensor }) => {
  const getIcon = (type: Sensor['type']) => {
    switch (type) {
      case 'RAIN_GAUGE':
        return CloudRain;
      case 'SOIL_MOISTURE':
        return Droplets;
      case 'RIVER_STAGE':
        return Waves;
      case 'TILT_METER':
        return Compass;
      default:
        return Droplets;
    }
  };

  const Icon = getIcon(sensor.type);

  const statusConfig = {
    HEALTHY: {
      bg: 'border-emerald-500/30 bg-slate-900',
      text: 'text-emerald-400',
      badge: 'bg-emerald-950 text-emerald-300 border-emerald-800',
      icon: CheckCircle2,
    },
    WARNING: {
      bg: 'border-orange-500/40 bg-slate-900',
      text: 'text-orange-400',
      badge: 'bg-orange-950 text-orange-300 border-orange-800',
      icon: AlertTriangle,
    },
    FAULT: {
      bg: 'border-purple-500/50 bg-slate-900',
      text: 'text-purple-400',
      badge: 'bg-purple-950 text-purple-300 border-purple-800 animate-pulse',
      icon: AlertTriangle,
    },
    OFFLINE: {
      bg: 'border-slate-800 bg-slate-950/60 opacity-60',
      text: 'text-slate-500',
      badge: 'bg-slate-900 text-slate-400 border-slate-700',
      icon: XCircle,
    },
  }[sensor.status];

  const StatusIcon = statusConfig.icon;

  return (
    <div className={`border rounded-xl p-3.5 font-mono text-xs shadow-md ${statusConfig.bg} select-none`}>
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800/80 pb-2 mb-2">
        <div className="flex items-center gap-2">
          <div className="p-1.5 rounded-lg bg-slate-950 border border-slate-800 text-orange-400">
            <Icon className="w-4 h-4" />
          </div>
          <div>
            <div className="font-bold text-slate-100">{sensor.villageName}</div>
            <div className="text-[10px] text-slate-500">{sensor.id}</div>
          </div>
        </div>

        <span className={`px-2 py-0.5 rounded border text-[10px] font-bold flex items-center gap-1 ${statusConfig.badge}`}>
          <StatusIcon className="w-3 h-3" />
          <span>{sensor.status}</span>
        </span>
      </div>

      {/* Telemetry Reading */}
      <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800/80 my-2">
        <div className="text-[10px] text-slate-400 uppercase tracking-wide">Live Reading</div>
        <div className="flex items-baseline gap-1.5 mt-0.5">
          <span className="text-xl font-black text-slate-100">{sensor.currentValue}</span>
          <span className="text-xs text-slate-400 font-sans">{sensor.unit}</span>
        </div>
      </div>

      {/* Anomaly Callout */}
      {sensor.anomalyFlag && sensor.anomalyDetails && (
        <div className="p-2 rounded bg-purple-950/40 border border-purple-800/50 text-[10px] text-purple-300 mb-2">
          <div className="font-bold flex items-center gap-1 text-purple-400">
            <AlertTriangle className="w-3 h-3" /> Telemetry Anomaly Detected
          </div>
          <div className="mt-0.5 leading-tight text-slate-300">{sensor.anomalyDetails}</div>
        </div>
      )}

      {/* Hardware Health Footer */}
      <div className="flex items-center justify-between text-[10px] text-slate-400 pt-1 border-t border-slate-800/60">
        <div className="flex items-center gap-1">
          <Battery className={`w-3.5 h-3.5 ${sensor.batteryPct < 25 ? 'text-red-400' : 'text-emerald-400'}`} />
          <span>{sensor.batteryPct}%</span>
        </div>

        <div className="flex items-center gap-1">
          <Signal className="w-3.5 h-3.5 text-slate-400" />
          <span>{sensor.signalStrengthDbm} dBm</span>
        </div>

        <span className="text-slate-500">{sensor.lastUpdated}</span>
      </div>
    </div>
  );
};
