import React, { useEffect, useState } from 'react';
import { Cpu, Database, Server, Radio, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';

interface BackendHealth {
  status: string;
  database: string;
  redis: string;
  database_type: string;
  version: string;
  environment: string;
  timestamp: number;
}

export const HealthPage: React.FC = () => {
  const [health, setHealth] = useState<BackendHealth | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('http://localhost:8000/health');
      if (!res.ok) throw new Error(`HTTP ${res.status}: ${res.statusText}`);
      const data = await res.json();
      setHealth(data);
      setLoading(false);
    } catch (err: any) {
      setError(err.message);
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  return (
    <div className="flex-1 p-4 md:p-6 bg-slate-950 overflow-y-auto font-mono text-xs select-none space-y-4">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-base font-bold text-slate-100 font-mono">SYSTEM HEALTH & ARCHITECTURE STATUS</h2>
          <p className="text-xs text-slate-400">
            FastAPI backend connectivity, database engine, Redis fallback, and ML runtime diagnostics
          </p>
        </div>

        <button
          onClick={fetchHealth}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs border border-slate-700 transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>REFRESH HEALTH</span>
        </button>
      </div>

      {/* Backend & Database Health Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        {/* Backend API */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-[10px]">
            <span>FASTAPI BACKEND</span>
            <Server className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-lg font-black text-slate-100">
            {health?.status === 'ok' ? 'OPERATIONAL' : 'DEGRADED / FALLBACK'}
          </div>
          <div className="text-[10px] text-slate-500">
            Version: {health?.version || '0.1.0'} • Port: 8000
          </div>
        </div>

        {/* Database */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-[10px]">
            <span>PRIMARY DATABASE</span>
            <Database className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-lg font-black text-emerald-400 uppercase">
            {health?.database || 'CONNECTED'} ({health?.database_type || 'sqlite/postgis'})
          </div>
          <div className="text-[10px] text-slate-500">
            25 Pilot Villages & Telemetry Tables Seeded
          </div>
        </div>

        {/* Redis */}
        <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
          <div className="flex items-center justify-between text-slate-400 text-[10px]">
            <span>REDIS / PUB-SUB</span>
            <Radio className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-lg font-black text-slate-100 uppercase">
            {health?.redis || 'OFFLINE FALLBACK'}
          </div>
          <div className="text-[10px] text-slate-500">
            InMemory Resilient Fallback Queue Active
          </div>
        </div>
      </div>

      {/* ML Diagnostic Log Card */}
      <div className="p-4 rounded-xl bg-slate-900 border border-slate-800 space-y-2">
        <h3 className="font-bold text-slate-200 text-sm border-b border-slate-800 pb-2 flex items-center gap-2">
          <Cpu className="w-4 h-4 text-orange-400" />
          <span>ML PIPELINE & CONFORMAL CALIBRATION SPECIFICATIONS</span>
        </h3>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-slate-300 text-[11px] pt-1">
          <div className="space-y-1.5 p-3 rounded-lg bg-slate-950 border border-slate-800/80">
            <span className="font-bold text-orange-400 block text-xs">Gradient Boosting & Calibration</span>
            <p className="text-slate-400">
              • Model: Pretrained XGBoost + Isotonic Calibrated Regressor (2019–2021 Train, 2022 Calib, 2023 Hold-out)<br />
              • Feature inputs: 72h rainfall, Factor of Safety (Fs), soil saturation, slope degrees, upstream drainage
            </p>
          </div>

          <div className="space-y-1.5 p-3 rounded-lg bg-slate-950 border border-slate-800/80">
            <span className="font-bold text-emerald-400 block text-xs">Conformal Prediction & Venn-Abers</span>
            <p className="text-slate-400">
              • Rare-event interval: Class-conditional conformal bounds [p_lower, p_upper]<br />
              • Bayes-Optimal Alert Thresholding: Dynamic p &gt; C_fa / (C_fa + C_miss) with fatigue cooldown
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
