import React from 'react';
import { RiskAssessment } from '../../types';
import { useTheme } from '../../context/ThemeContext';

interface RiskTimelineProps {
  risk: RiskAssessment;
  height?: number;
}

export const RiskTimeline: React.FC<RiskTimelineProps> = ({ risk, height = 180 }) => {
  const { isDark } = useTheme();
  const gridColor = isDark ? '#1e293b' : '#e2e8f0';
  const labelColor = isDark ? '#94a3b8' : '#475569';
  const pointBorder = isDark ? '#0f172a' : '#ffffff';
  // Generate realistic 12-hour history + 6-hour forecast points based on village explanation
  const points = [
    { t: '-12h', rain: 4.2, sat: 45, prob: 0.05, type: 'observed' },
    { t: '-9h', rain: 12.0, sat: 56, prob: 0.12, type: 'observed' },
    { t: '-6h', rain: 28.5, sat: 72, prob: 0.28, type: 'observed' },
    { t: '-3h', rain: 42.0, sat: 86, prob: 0.58, type: 'observed' },
    { t: '-1h', rain: risk.explanation.currentRainfallRateMmH * 0.9, sat: risk.explanation.soilSaturationPct * 0.95, prob: risk.probability * 0.9, type: 'observed' },
    { t: 'NOW', rain: risk.explanation.currentRainfallRateMmH, sat: risk.explanation.soilSaturationPct, prob: risk.probability, type: 'current' },
    { t: '+1h', rain: risk.explanation.currentRainfallRateMmH * 1.15, sat: Math.min(100, risk.explanation.soilSaturationPct * 1.03), prob: Math.min(0.99, risk.probability * 1.15), type: 'predicted' },
    { t: '+2h', rain: risk.explanation.currentRainfallRateMmH * 1.3, sat: Math.min(100, risk.explanation.soilSaturationPct * 1.06), prob: Math.min(0.99, risk.probability * 1.25), type: 'predicted' },
    { t: '+4h', rain: risk.explanation.currentRainfallRateMmH * 0.8, sat: Math.min(100, risk.explanation.soilSaturationPct * 1.02), prob: Math.max(0.1, risk.probability * 0.95), type: 'predicted' },
    { t: '+6h', rain: 12.0, sat: 85, prob: 0.35, type: 'predicted' },
  ];

  const w = 480;
  const h = height;
  const padX = 40;
  const padY = 25;

  const maxRain = 60; // mm/h max scale
  const getX = (i: number) => padX + (i / (points.length - 1)) * (w - 2 * padX);
  const getYProb = (p: number) => h - padY - p * (h - 2 * padY);
  const getYRain = (r: number) => h - padY - (r / maxRain) * (h - 2 * padY);

  const probPath = points.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getYProb(pt.prob)}`).join(' ');
  const rainPath = points.map((pt, i) => `${i === 0 ? 'M' : 'L'} ${getX(i)} ${getYRain(pt.rain)}`).join(' ');

  const nowIndex = 5;
  const nowX = getX(nowIndex);

  return (
    <div className="bg-slate-950/80 rounded-lg p-3 border border-slate-800 text-xs font-mono select-none">
      <div className="flex items-center justify-between mb-2 pb-1.5 border-b border-slate-800/80">
        <span className="text-[11px] font-bold text-slate-300">OBSERVED VS PREDICTED TRAJECTORY</span>
        <div className="flex items-center gap-3 text-[10px]">
          <span className="flex items-center gap-1 text-red-400">
            <span className="w-2.5 h-0.5 bg-red-400 inline-block" /> Failure Prob
          </span>
          <span className="flex items-center gap-1 text-blue-400">
            <span className="w-2.5 h-0.5 bg-blue-400 inline-block" /> Rainfall (mm/h)
          </span>
        </div>
      </div>

      <svg viewBox={`0 0 ${w} ${h}`} className="w-full overflow-visible">
        {/* Background Grid Lines */}
        {[0, 0.25, 0.5, 0.75, 1.0].map((level) => {
          const y = getYProb(level);
          return (
            <g key={level}>
              <line x1={padX} y1={y} x2={w - padX} y2={y} stroke={gridColor} strokeDasharray="3 3" />
              <text x={padX - 6} y={y + 3} textAnchor="end" fill={labelColor} fontSize="9">
                {Math.round(level * 100)}%
              </text>
            </g>
          );
        })}

        {/* Observed vs Forecast Boundary Shading */}
        <rect x={nowX} y={padY} width={w - padX - nowX} height={h - 2 * padY} fill="#f97316" fillOpacity={isDark ? 0.04 : 0.08} />

        {/* Vertical NOW line */}
        <line x1={nowX} y1={padY - 8} x2={nowX} y2={h - padY + 6} stroke="#f97316" strokeWidth="1.5" strokeDasharray="4 2" />
        <text x={nowX} y={padY - 12} textAnchor="middle" fill="#ea580c" fontSize="9" fontWeight="bold">
          CURRENT (T₀)
        </text>

        {/* Rainfall Line (Blue) */}
        <path d={rainPath} fill="none" stroke="#2563eb" strokeWidth="2" strokeOpacity="0.85" />

        {/* Landslide Risk Probability Line (Red / Gradient) */}
        <path d={probPath} fill="none" stroke="#dc2626" strokeWidth="2.5" />

        {/* Points */}
        {points.map((pt, i) => {
          const x = getX(i);
          const yP = getYProb(pt.prob);
          const isNow = pt.type === 'current';
          return (
            <g key={i}>
              <circle
                cx={x}
                cy={yP}
                r={isNow ? 4.5 : 2.5}
                fill={isNow ? '#dc2626' : pt.type === 'predicted' ? '#ea580c' : '#64748b'}
                stroke={pointBorder}
                strokeWidth="1.5"
              />
              <text x={x} y={h - padY + 14} textAnchor="middle" fill={isNow ? '#ea580c' : labelColor} fontSize="8.5">
                {pt.t}
              </text>
            </g>
          );
        })}
      </svg>

      <div className="flex items-center justify-between text-[10px] text-slate-500 pt-2 border-t border-slate-800/60 mt-2">
        <span>← HISTORICAL TELEMETRY (12h)</span>
        <span className="text-orange-400 font-bold">ESTIMATED LEAD TIME: ~{risk.leadTimeMinutes} MIN</span>
        <span>NOWCAST FORECAST (6h) →</span>
      </div>
    </div>
  );
};
