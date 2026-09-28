import React, { useState, useEffect, useRef, useCallback } from 'react';
import {
  History, Play, Pause, SkipForward, RotateCcw,
  Wifi, WifiOff, AlertTriangle, ShieldCheck, Radio, Volume2,
  Clock, Footprints, ChevronRight, TrendingUp, Zap,
} from 'lucide-react';
import { fetchScenarios, runReplay, ReplayFrame, ReplayResult, ScenarioInfo } from '../../services/replayService';

// ── Helpers ────────────────────────────────────────────────────────────────

const TIER_COLOR: Record<string, string> = {
  NONE: 'text-slate-400 bg-slate-900 border-slate-700',
  WATCH: 'text-yellow-300 bg-yellow-950 border-yellow-700',
  WARNING: 'text-orange-300 bg-orange-950 border-orange-600',
  EVACUATE: 'text-red-300 bg-red-950 border-red-500 animate-pulse',
};

const TIER_DOT: Record<string, string> = {
  NONE: 'bg-slate-500', WATCH: 'bg-yellow-400', WARNING: 'bg-orange-400', EVACUATE: 'bg-red-400',
};

const SPEED_MS: Record<string, number> = {
  '1×': 3500, '2×': 1800, '5×': 700, 'Instant': 0,
};

function fmt(n: number, d = 1) { return n.toFixed(d); }

function ProbBar({ prob, lo, hi }: { prob: number; lo: number; hi: number }) {
  const pct = (v: number) => `${(v * 100).toFixed(1)}%`;
  return (
    <div className="relative h-4 w-full rounded bg-slate-800 overflow-hidden mt-1">
      {/* CI band */}
      <div
        className="absolute top-0 bottom-0 bg-blue-900/60"
        style={{ left: `${lo * 100}%`, width: `${(hi - lo) * 100}%` }}
      />
      {/* Point estimate */}
      <div
        className="absolute top-0 bottom-0 w-0.5 bg-blue-400"
        style={{ left: `${prob * 100}%` }}
      />
      <div className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white">
        {pct(prob)} [{pct(lo)}–{pct(hi)}]
      </div>
    </div>
  );
}

function ChannelRow({ ch }: { ch: ReplayFrame['active_channels'][0] }) {
  const icon = ch.offline_fallback
    ? <Radio className="w-3.5 h-3.5 text-purple-400" />
    : <Wifi className="w-3.5 h-3.5 text-sky-400" />;
  const status = ch.delivered
    ? <span className="text-emerald-400 font-bold">✓ {ch.latency_s.toFixed(1)}s</span>
    : <span className="text-red-400 font-bold">✗ offline</span>;
  return (
    <div className="flex items-center justify-between px-2 py-1 rounded bg-slate-950 border border-slate-800">
      <div className="flex items-center gap-1.5 text-slate-300">{icon}<span>{ch.channel}</span></div>
      <div className="text-[11px]">{status}</div>
    </div>
  );
}

function Gauge({ label, value, unit, color }: { label: string; value: number; unit: string; color: string }) {
  return (
    <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 text-center">
      <div className="text-[10px] text-slate-500 uppercase tracking-wider">{label}</div>
      <div className={`text-lg font-bold font-mono ${color}`}>{fmt(value, value < 10 ? 2 : 1)}</div>
      <div className="text-[10px] text-slate-600">{unit}</div>
    </div>
  );
}

// ── Main Component ─────────────────────────────────────────────────────────

export const EventReplay: React.FC = () => {
  const [scenarios, setScenarios] = useState<ScenarioInfo[]>([]);
  const [selectedScenarioId, setSelectedScenarioId] = useState('bhatwari_debris_flow_synthetic');
  const [killInternet, setKillInternet] = useState(false);
  const [speed, setSpeed] = useState<string>('2×');
  const [result, setResult] = useState<ReplayResult | null>(null);
  const [currentStep, setCurrentStep] = useState(0);
  const [isPlaying, setIsPlaying] = useState(false);
  const [loading, setLoading] = useState(false);
  const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load scenarios on mount
  useEffect(() => {
    fetchScenarios().then(setScenarios);
  }, []);

  // Load replay data whenever scenario or kill-internet changes
  const loadReplay = useCallback(async () => {
    setLoading(true);
    setIsPlaying(false);
    setCurrentStep(0);
    const data = await runReplay(selectedScenarioId, killInternet, 1.0);
    setResult(data);
    setLoading(false);
  }, [selectedScenarioId, killInternet]);

  useEffect(() => { loadReplay(); }, [loadReplay]);

  // Playback timer
  useEffect(() => {
    if (timerRef.current) clearInterval(timerRef.current);
    if (!isPlaying || !result) return;

    const delay = SPEED_MS[speed];
    if (delay === 0) {
      // Instant: jump to last frame
      setCurrentStep(result.frames.length - 1);
      setIsPlaying(false);
      return;
    }
    timerRef.current = setInterval(() => {
      setCurrentStep(prev => {
        if (prev >= (result?.frames.length ?? 1) - 1) {
          setIsPlaying(false);
          return prev;
        }
        return prev + 1;
      });
    }, delay);
    return () => { if (timerRef.current) clearInterval(timerRef.current); };
  }, [isPlaying, speed, result]);

  const frame: ReplayFrame | null = result?.frames[currentStep] ?? null;
  const summary = result?.summary;

  const handleReset = () => {
    setIsPlaying(false);
    setCurrentStep(0);
  };

  const handleStep = () => {
    setIsPlaying(false);
    setCurrentStep(prev => Math.min((result?.frames.length ?? 1) - 1, prev + 1));
  };

  const tierOrder: Record<string, number> = { NONE: 0, WATCH: 1, WARNING: 2, EVACUATE: 3 };
  const ewsFirstIdx = result?.frames.findIndex(f => tierOrder[f.ews_tier] >= 1) ?? -1;
  const baseFirstIdx = result?.frames.findIndex(f => f.baseline_alert_active) ?? -1;

  return (
    <div className="space-y-3 font-mono text-xs select-none">

      {/* ── Synthetic Disclaimer Banner ── */}
      <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-950/70 border border-amber-700/60 text-amber-300 text-[11px] font-bold">
        <AlertTriangle className="w-3.5 h-3.5 flex-shrink-0" />
        SYNTHETIC EVENT — calibrated from Kedarnath 2013 analog data. NOT real sensor records.
      </div>

      {/* ── Header + Controls ── */}
      <div className="p-3 rounded-xl bg-slate-900 border border-slate-800 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <History className="w-4 h-4 text-white" />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-100">Disaster Event Replay</div>
              <div className="text-[10px] text-slate-400">EWS pipeline vs IMD static-threshold baseline</div>
            </div>
          </div>

          {/* Kill Internet Toggle */}
          <button
            onClick={() => setKillInternet(v => !v)}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg border font-bold text-[11px] transition-all ${
              killInternet
                ? 'bg-red-950 border-red-600 text-red-300 shadow-lg shadow-red-950'
                : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500'
            }`}
          >
            {killInternet ? <WifiOff className="w-3.5 h-3.5" /> : <Wifi className="w-3.5 h-3.5" />}
            {killInternet ? '🔴 INTERNET KILLED' : 'Kill Internet'}
          </button>
        </div>

        {/* Scenario + Speed Row */}
        <div className="flex flex-wrap items-center gap-2">
          <select
            value={selectedScenarioId}
            onChange={e => setSelectedScenarioId(e.target.value)}
            className="flex-1 min-w-[180px] bg-slate-800 border border-slate-700 rounded-lg px-2 py-1.5 text-slate-200 text-[11px] focus:outline-none focus:ring-1 focus:ring-blue-600"
          >
            {scenarios.map(s => (
              <option key={s.id} value={s.id}>{s.name}</option>
            ))}
          </select>

          {/* Speed buttons */}
          <div className="flex items-center gap-1">
            {Object.keys(SPEED_MS).map(s => (
              <button
                key={s}
                onClick={() => setSpeed(s)}
                className={`px-2 py-1 rounded text-[10px] font-bold border transition-colors ${
                  speed === s
                    ? 'bg-blue-700 border-blue-500 text-white'
                    : 'bg-slate-800 border-slate-700 text-slate-400 hover:border-slate-500'
                }`}
              >
                {s}
              </button>
            ))}
          </div>

          {/* Playback buttons */}
          <div className="flex items-center gap-1.5">
            <button onClick={() => setIsPlaying(v => !v)} disabled={loading}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-orange-600 hover:bg-orange-500 text-white font-bold text-[11px] transition-colors disabled:opacity-40">
              {isPlaying ? <Pause className="w-3.5 h-3.5" /> : <Play className="w-3.5 h-3.5" />}
              {isPlaying ? 'PAUSE' : 'PLAY'}
            </button>
            <button onClick={handleStep} disabled={loading || !result}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 disabled:opacity-40">
              <SkipForward className="w-3.5 h-3.5" />
            </button>
            <button onClick={handleReset} disabled={loading}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 disabled:opacity-40">
              <RotateCcw className="w-3.5 h-3.5" />
            </button>
          </div>
        </div>
      </div>

      {loading && (
        <div className="text-center py-8 text-slate-400">Loading replay…</div>
      )}

      {!loading && result && frame && (
        <>
          {/* ── Summary Cards: EWS vs Baseline ── */}
          <div className="grid grid-cols-2 gap-2">
            {/* EWS Card */}
            <div className="p-3 rounded-xl bg-emerald-950/60 border border-emerald-700/50 space-y-1">
              <div className="flex items-center gap-1.5 text-emerald-400 font-bold text-[11px]">
                <Zap className="w-3.5 h-3.5" /> AI EWS (Multi-Source)
              </div>
              <div className="text-xl font-black text-emerald-300">{summary?.ews_first_alert_hour ?? '—'}</div>
              <div className="text-[10px] text-emerald-600">First alert dispatched</div>
              <div className="text-[10px] text-slate-400">
                Reach: {killInternet ? `${summary?.kill_internet_local_reach_pct ?? 0}% (local only)` : `${summary?.online_reach_pct ?? 0}%`}
              </div>
            </div>
            {/* Baseline Card */}
            <div className="p-3 rounded-xl bg-slate-900 border border-slate-700 space-y-1">
              <div className="flex items-center gap-1.5 text-slate-400 font-bold text-[11px]">
                <TrendingUp className="w-3.5 h-3.5" /> IMD Threshold Baseline
              </div>
              <div className="text-xl font-black text-slate-300">{summary?.baseline_first_alert_hour ?? '—'}</div>
              <div className="text-[10px] text-slate-500">First threshold breach</div>
              {(summary?.extra_lead_time_hours ?? 0) > 0 && (
                <div className="mt-1 px-2 py-0.5 rounded bg-emerald-900/60 border border-emerald-700/40 text-emerald-300 font-black text-[11px] text-center">
                  +{summary?.extra_lead_time_hours.toFixed(1)}h ADVANCE NOTICE
                </div>
              )}
            </div>
          </div>

          {/* ── Timeline Scrubber ── */}
          <div className="flex gap-1 p-1 rounded-xl bg-slate-950 border border-slate-800 overflow-x-auto">
            {result.frames.map((f, idx) => {
              const isEwsFirst = idx === ewsFirstIdx;
              const isBaseFirst = idx === baseFirstIdx;
              return (
                <button
                  key={idx}
                  onClick={() => { setIsPlaying(false); setCurrentStep(idx); }}
                  className={`relative flex-shrink-0 px-2 py-2 rounded-lg text-center border transition-all min-w-[52px] ${
                    currentStep === idx
                      ? 'bg-orange-600 border-orange-400 text-white font-bold shadow-md'
                      : idx < currentStep
                      ? 'bg-slate-900 border-slate-800 text-slate-300'
                      : 'bg-slate-950/40 border-slate-900 text-slate-600'
                  }`}
                >
                  <div className="text-[10px] font-bold">
                    {f.hour_offset === 0 ? 'T±0' : f.hour_offset > 0 ? `T+${f.hour_offset}h` : `T${f.hour_offset}h`}
                  </div>
                  <div className={`w-2 h-2 rounded-full mx-auto mt-0.5 ${TIER_DOT[f.ews_tier]}`} />
                  {isEwsFirst && (
                    <div className="absolute -top-1.5 left-1/2 -translate-x-1/2 text-[8px] text-emerald-400 font-black whitespace-nowrap">EWS▲</div>
                  )}
                  {isBaseFirst && (
                    <div className="absolute -bottom-1.5 left-1/2 -translate-x-1/2 text-[8px] text-slate-400 font-black whitespace-nowrap">Base▼</div>
                  )}
                </button>
              );
            })}
          </div>

          {/* ── Current Frame Dossier ── */}
          <div className="p-3.5 rounded-xl bg-slate-900 border border-slate-800 space-y-3 shadow-lg">
            {/* Frame Header */}
            <div className="flex items-center justify-between flex-wrap gap-2 border-b border-slate-800 pb-2.5">
              <div>
                <div className="text-[10px] text-orange-400 font-bold uppercase tracking-widest">
                  {frame.is_impact_time ? '💥 EVENT IMPACT' : `Frame ${currentStep + 1} / ${result.frames.length}`}
                </div>
                <div className="text-sm font-bold text-slate-100">
                  {frame.hour_offset === 0 ? 'T ± 0' : frame.hour_offset > 0 ? `T + ${frame.hour_offset}h` : `T − ${Math.abs(frame.hour_offset)}h`}
                  &nbsp;·&nbsp;
                  <span className="text-slate-400 font-normal">{frame.phase_label}</span>
                </div>
              </div>
              {/* EWS Tier Badge */}
              <div className={`px-3 py-1.5 rounded-lg border font-black text-sm ${TIER_COLOR[frame.ews_tier]}`}>
                {frame.ews_tier}
              </div>
            </div>

            {/* Telemetry Gauges */}
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
              <Gauge label="1h Rain" value={frame.telemetry.rainfall_1h_mm} unit="mm/h" color="text-blue-400" />
              <Gauge label="24h Rain" value={frame.telemetry.rainfall_24h_mm} unit="mm" color="text-blue-300" />
              <Gauge label="Soil Sat" value={frame.telemetry.soil_saturation_pct} unit="%" color="text-cyan-400" />
              <Gauge label="River" value={frame.telemetry.river_stage_m} unit="m" color="text-orange-400" />
              <Gauge label="Fs" value={frame.factor_of_safety} unit="stability" color={frame.factor_of_safety < 1.0 ? 'text-red-400' : frame.factor_of_safety < 1.3 ? 'text-orange-300' : 'text-emerald-400'} />
              <Gauge label="Reach" value={frame.delivery_reach_pct} unit="%" color="text-purple-400" />
            </div>

            {/* ML Probability + Venn-Abers Bounds */}
            <div className="space-y-1">
              <div className="flex items-center justify-between text-[11px]">
                <span className="text-slate-400 font-bold">ML FAILURE PROB (Venn-Abers CI)</span>
                <span className="text-blue-300 font-bold">{(frame.ml_calibrated_prob * 100).toFixed(1)}%</span>
              </div>
              <ProbBar prob={frame.ml_calibrated_prob} lo={frame.conformal_lower} hi={frame.conformal_upper} />
            </div>

            {/* Baseline vs EWS diff row */}
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="p-2 rounded-lg bg-emerald-950/40 border border-emerald-800/40">
                <div className="text-emerald-500 font-bold mb-0.5">EWS TIER</div>
                <div className={`font-black ${frame.ews_tier === 'EVACUATE' ? 'text-red-400' : frame.ews_tier === 'WARNING' ? 'text-orange-400' : frame.ews_tier === 'WATCH' ? 'text-yellow-400' : 'text-slate-500'}`}>
                  {frame.ews_tier}
                </div>
              </div>
              <div className="p-2 rounded-lg bg-slate-950 border border-slate-800">
                <div className="text-slate-500 font-bold mb-0.5">BASELINE TIER</div>
                <div className={`font-black ${frame.baseline_alert_active ? 'text-orange-400' : 'text-slate-600'}`}>
                  {frame.baseline_alert_active ? frame.baseline_tier : 'NO ALERT'}
                </div>
                {frame.baseline_threshold_rule !== '—' && (
                  <div className="text-[10px] text-slate-600">{frame.baseline_threshold_rule}</div>
                )}
              </div>
            </div>

            {/* Evacuation Margin */}
            {frame.ews_tier !== 'NONE' && (
              <div className="p-2.5 rounded-lg bg-slate-950 border border-slate-800 space-y-1">
                <div className="text-[10px] text-slate-500 font-bold uppercase tracking-wider">Evacuation Window</div>
                <div className="grid grid-cols-3 gap-1.5 text-center text-[11px]">
                  <div>
                    <div className="text-slate-500">To Impact</div>
                    <div className="font-black text-orange-300 text-sm">{frame.time_to_impact_min.toFixed(0)} min</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Evacuate</div>
                    <div className="font-black text-yellow-300 text-sm">{frame.time_to_evacuate_min.toFixed(0)} min</div>
                  </div>
                  <div>
                    <div className="text-slate-500">Margin</div>
                    <div className={`font-black text-sm ${frame.available_margin_min > 30 ? 'text-emerald-400' : frame.available_margin_min > 0 ? 'text-yellow-400' : 'text-red-400'}`}>
                      {frame.available_margin_min.toFixed(0)} min
                    </div>
                  </div>
                </div>
                <div className="text-[10px] text-slate-400 flex items-center gap-1">
                  <ChevronRight className="w-3 h-3" />
                  Route: <span className="text-slate-200 font-bold ml-1">{frame.safe_route_name}</span>
                  &nbsp;→ <span className="text-slate-300 ml-1">{frame.shelter_name}</span>
                </div>
                {frame.severed_routes.length > 0 && (
                  <div className="text-[10px] text-red-400 flex items-center gap-1">
                    <AlertTriangle className="w-3 h-3" />
                    Severed: {frame.severed_routes.join(', ')}
                  </div>
                )}
              </div>
            )}

            {/* Channel Delivery */}
            {frame.ews_tier !== 'NONE' && (
              <div className="space-y-1">
                <div className="flex items-center justify-between text-[10px] text-slate-500 font-bold uppercase tracking-wider">
                  <span>Alert Channels</span>
                  {frame.internet_killed && (
                    <span className="text-red-400 flex items-center gap-1">
                      <WifiOff className="w-3 h-3" /> Internet: KILLED
                    </span>
                  )}
                </div>
                <div className="space-y-1">
                  {frame.active_channels.map((ch, i) => (
                    <ChannelRow key={i} ch={ch} />
                  ))}
                </div>
              </div>
            )}

            {/* Alert Messages */}
            {frame.alert_message_en && (
              <div className="space-y-1.5">
                <div className="text-[10px] text-slate-500 font-bold uppercase">Alert Messages</div>
                <div className="p-2 rounded-lg bg-red-950/40 border border-red-800/40 text-[11px] text-red-200 leading-snug">
                  🇬🇧 {frame.alert_message_en}
                </div>
                <div className="p-2 rounded-lg bg-red-950/30 border border-red-800/30 text-[11px] text-red-200 leading-snug">
                  🇮🇳 {frame.alert_message_hi}
                </div>
              </div>
            )}

            {/* Analog Match */}
            {frame.analog_match_event && (
              <div className="p-2 rounded-lg bg-slate-950 border border-slate-800 text-[11px] space-y-0.5">
                <div className="text-slate-500 font-bold">ANALOG MATCH</div>
                <div className="text-slate-300">{frame.analog_match_event} — {frame.analog_similarity_pct}% similarity</div>
                <div className="text-slate-500">{frame.explanation_summary}</div>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
};
