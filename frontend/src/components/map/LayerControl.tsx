import React, { useState } from 'react';
import { Layers, Eye, EyeOff, X } from 'lucide-react';

export interface ActiveLayers {
  villages: boolean;
  sensors: boolean;
  routes: boolean;
  shelters: boolean;
  rainHeatmap: boolean;
  citizenReports: boolean;
  baseLayer: 'streets' | 'terrain' | 'satellite' | 'dark';
}

interface LayerControlProps {
  layers: ActiveLayers;
  onToggleLayer: (key: keyof ActiveLayers) => void;
  onSetBaseLayer: (base: 'streets' | 'terrain' | 'satellite' | 'dark') => void;
}

export const LayerControl: React.FC<LayerControlProps> = ({
  layers,
  onToggleLayer,
  onSetBaseLayer,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="flex items-center gap-2 px-3 py-2 rounded-lg bg-slate-950/95 hover:bg-slate-900 border border-slate-800 text-slate-200 hover:text-white text-xs font-mono shadow-2xl backdrop-blur transition-all active:scale-95"
        title="Open Map Layers"
      >
        <Layers className="w-4 h-4 text-orange-400" />
        <span className="font-bold">Layers</span>
      </button>
    );
  }

  return (
    <div className="bg-slate-950/95 border border-slate-800 rounded-lg p-3 text-xs font-mono shadow-2xl backdrop-blur max-w-xs select-none">
      <div className="flex items-center justify-between gap-2 border-b border-slate-800 pb-2 mb-2 text-slate-300 font-bold">
        <div className="flex items-center gap-1.5">
          <Layers className="w-4 h-4 text-orange-400" />
          <span>GIS MAP LAYERS</span>
        </div>
        <button
          onClick={() => setIsOpen(false)}
          className="p-1 rounded text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          title="Minimize Layers"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* Base Layer Switcher */}
      <div className="mb-3">
        <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">
          Base Style (Zero API Key)
        </label>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-1">
          {(['streets', 'terrain', 'satellite', 'dark'] as const).map((mode) => (
            <button
              key={mode}
              onClick={() => onSetBaseLayer(mode)}
              className={`px-2 py-1 rounded text-[10px] capitalize border transition-all ${
                layers.baseLayer === mode
                  ? 'bg-orange-600 border-orange-400 text-white font-bold'
                  : 'bg-slate-900 border-slate-800 text-slate-400 hover:text-white'
              }`}
            >
              {mode}
            </button>
          ))}
        </div>
      </div>

      {/* Overlays Toggle */}
      <div>
        <label className="text-[10px] text-slate-500 uppercase tracking-wider block mb-1">
          Active Overlays
        </label>
        <div className="space-y-1">
          {[
            { key: 'villages', label: 'Village Risk Nodes', count: '25' },
            { key: 'citizenReports', label: 'Citizen Ground Reports', count: 'Live' },
            { key: 'routes', label: 'Evacuation Trails & Highway', count: '16' },
            { key: 'shelters', label: 'High-Ground Shelters', count: '8' },
            { key: 'sensors', label: 'IoT Telemetry Sensors', count: '6' },
            { key: 'rainHeatmap', label: 'Precipitation Grid', count: 'Radar' },
          ].map((item) => {
            const isEnabled = layers[item.key as keyof ActiveLayers] as boolean;
            return (
              <button
                key={item.key}
                onClick={() => onToggleLayer(item.key as keyof ActiveLayers)}
                className={`w-full flex items-center justify-between px-2 py-1.5 rounded border transition-colors ${
                  isEnabled
                    ? 'bg-slate-900/90 border-slate-700 text-slate-200 font-medium'
                    : 'bg-slate-950/40 border-slate-800/40 text-slate-500 hover:text-slate-400'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  {isEnabled ? (
                    <Eye className="w-3.5 h-3.5 text-orange-400" />
                  ) : (
                    <EyeOff className="w-3.5 h-3.5 text-slate-600" />
                  )}
                  <span>{item.label}</span>
                </div>
                <span className="text-[10px] px-1 rounded bg-slate-800 text-slate-400">
                  {item.count}
                </span>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
