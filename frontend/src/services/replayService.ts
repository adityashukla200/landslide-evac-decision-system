/**
 * replayService.ts
 * Client for the Replay Engine REST API.
 * Falls back to calibrated synthetic mock data when the backend is unavailable.
 */

const BASE_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000';

// ── Types ──────────────────────────────────────────────────────────────────

export interface ChannelDelivery {
  channel: string;
  delivered: boolean;
  offline_fallback: boolean;
  latency_s: number;
}

export interface ReplayFrame {
  step_index: number;
  hour_offset: number;           // negative = before impact, 0 = event
  timestamp: string;
  phase_label: string;
  is_impact_time: boolean;

  // Telemetry
  telemetry: {
    rainfall_1h_mm: number;
    rainfall_24h_mm: number;
    rainfall_72h_mm: number;
    soil_saturation_pct: number;
    river_stage_m: number;
    slope_angle_deg: number;
  };

  // Physics & ML
  factor_of_safety: number;
  ml_calibrated_prob: number;
  conformal_lower: number;
  conformal_upper: number;
  ews_tier: 'NONE' | 'WATCH' | 'WARNING' | 'EVACUATE';

  // Baseline comparison
  baseline_alert_active: boolean;
  baseline_tier: string;
  baseline_threshold_rule: string;
  lead_time_gain_hours: number;

  // Analog
  analog_match_event: string;
  analog_similarity_pct: number;
  explanation_summary: string;

  // Evacuation
  time_to_impact_min: number;
  time_to_evacuate_min: number;
  available_margin_min: number;
  safe_route_id: string;
  safe_route_name: string;
  severed_routes: string[];
  shelter_name: string;

  // Channels
  internet_killed: boolean;
  active_channels: ChannelDelivery[];
  delivery_reach_pct: number;

  // Messages
  alert_message_en: string;
  alert_message_hi: string;
}

export interface ReplaySummary {
  scenario_id: string;
  total_frames: number;
  ews_first_alert_hour: string;
  baseline_first_alert_hour: string;
  extra_lead_time_hours: number;
  internet_killed: boolean;
  kill_internet_local_reach_pct: number;
  online_reach_pct: number;
}

export interface ReplayResult {
  scenario: {
    id: string;
    name: string;
    description: string;
    location: string;
    is_synthetic: boolean;
    data_source_label: string;
  };
  summary: ReplaySummary;
  frames: ReplayFrame[];
}

export interface ScenarioInfo {
  id: string;
  name: string;
  description: string;
  location: string;
  is_synthetic: boolean;
  step_count: number;
}

// ── Mock Data ──────────────────────────────────────────────────────────────

const BHATWARI_MOCK_FRAMES: ReplayFrame[] = (() => {
  const steps = [
    { h: -12, r1: 4.2,  r24: 18.6,  r72: 42.1,  sat: 38.0, rv: 1.1, slope: 31.5, prob: 0.014, lo: 0.009, hi: 0.022, fs: 2.31, tier: 'WATCH',    base: false },
    { h: -11, r1: 7.1,  r24: 26.3,  r72: 50.4,  sat: 43.2, rv: 1.2, slope: 31.5, prob: 0.021, lo: 0.014, hi: 0.032, fs: 2.18, tier: 'WATCH',    base: false },
    { h: -10, r1: 12.5, r24: 38.8,  r72: 63.2,  sat: 51.4, rv: 1.4, slope: 31.5, prob: 0.038, lo: 0.026, hi: 0.054, fs: 2.02, tier: 'WATCH',    base: false },
    { h: -9,  r1: 18.3, r24: 57.1,  r72: 81.5,  sat: 59.7, rv: 1.7, slope: 31.5, prob: 0.067, lo: 0.048, hi: 0.091, fs: 1.84, tier: 'WATCH',    base: false },
    { h: -8,  r1: 24.6, r24: 81.7,  r72: 106.3, sat: 66.8, rv: 2.1, slope: 31.5, prob: 0.112, lo: 0.083, hi: 0.147, fs: 1.64, tier: 'WATCH',    base: false },
    { h: -7,  r1: 31.2, r24: 112.9, r72: 144.1, sat: 73.5, rv: 2.6, slope: 31.5, prob: 0.178, lo: 0.138, hi: 0.224, fs: 1.42, tier: 'WARNING',  base: false },
    { h: -6,  r1: 38.4, r24: 151.3, r72: 189.7, sat: 79.8, rv: 3.2, slope: 31.5, prob: 0.267, lo: 0.221, hi: 0.318, fs: 1.24, tier: 'WARNING',  base: false },
    { h: -5,  r1: 64.0, r24: 215.3, r72: 243.7, sat: 85.2, rv: 3.9, slope: 31.5, prob: 0.391, lo: 0.341, hi: 0.444, fs: 1.09, tier: 'WARNING',  base: true  },
    { h: -4,  r1: 52.3, r24: 267.6, r72: 296.0, sat: 89.6, rv: 4.5, slope: 31.5, prob: 0.531, lo: 0.478, hi: 0.584, fs: 0.97, tier: 'EVACUATE', base: true  },
    { h: -3,  r1: 48.7, r24: 316.3, r72: 348.7, sat: 92.8, rv: 4.9, slope: 31.5, prob: 0.672, lo: 0.621, hi: 0.721, fs: 0.89, tier: 'EVACUATE', base: true  },
    { h: -2,  r1: 44.1, r24: 360.4, r72: 392.8, sat: 95.3, rv: 5.2, slope: 31.5, prob: 0.791, lo: 0.744, hi: 0.834, fs: 0.83, tier: 'EVACUATE', base: true  },
    { h: -1,  r1: 39.8, r24: 400.2, r72: 432.6, sat: 97.4, rv: 5.5, slope: 31.5, prob: 0.887, lo: 0.847, hi: 0.921, fs: 0.78, tier: 'EVACUATE', base: true  },
    { h:  0,  r1: 35.2, r24: 435.4, r72: 467.8, sat: 99.1, rv: 5.7, slope: 31.5, prob: 0.951, lo: 0.922, hi: 0.971, fs: 0.74, tier: 'EVACUATE', base: true  },
    { h:  1,  r1: 22.1, r24: 457.5, r72: 490.0, sat: 98.7, rv: 5.4, slope: 31.5, prob: 0.961, lo: 0.934, hi: 0.980, fs: 0.72, tier: 'EVACUATE', base: true  },
    { h:  2,  r1: 14.3, r24: 471.8, r72: 503.4, sat: 97.2, rv: 5.1, slope: 31.5, prob: 0.944, lo: 0.914, hi: 0.966, fs: 0.75, tier: 'EVACUATE', base: true  },
    { h:  3,  r1: 8.4,  r24: 480.2, r72: 511.8, sat: 95.3, rv: 4.8, slope: 31.5, prob: 0.918, lo: 0.884, hi: 0.945, fs: 0.79, tier: 'EVACUATE', base: true  },
  ];

  const TIER_ORDER: Record<string, number> = { NONE: 0, WATCH: 1, WARNING: 2, EVACUATE: 3 };

  return steps.map((s, idx) => {
    const isImpact = s.h === 0;
    const margin = Math.max(0, (-s.h) * 60 - 55);   // simplified: 55 min to evacuate
    const severed: string[] = s.h >= -2 ? ['Route A (Debris Fan)'] : [];
    const online = !false;  // mock always online
    const reach = 94.2;
    const enTier = s.tier === 'NONE' ? '' : s.tier === 'WATCH' ? 'WATCH advisory' : s.tier === 'WARNING' ? 'WARNING issued' : 'EVACUATE NOW';
    const msgEn = s.tier === 'EVACUATE'
      ? 'EVACUATE NOW. Go via Ridge Path B to Inter College Shelter. ~40 min.'
      : s.tier === 'WARNING'
      ? 'Flash flood WARNING: Bhatwari. Prepare to evacuate. Siren=evacuate.'
      : s.tier === 'WATCH'
      ? 'Flood WATCH: Bhatwari. Stay alert. Avoid riverside.'
      : '';
    const msgHi = s.tier === 'EVACUATE'
      ? 'अभी निकलें। रिज पथ B से इंटर कॉलेज आश्रय जाएं। लगभग 40 मिनट।'
      : s.tier === 'WARNING'
      ? 'बाढ़ चेतावनी: भटवाड़ी। निकासी के लिए तैयार रहें। सायरन=निकासी।'
      : s.tier === 'WATCH'
      ? 'बाढ़ सतर्कता: भटवाड़ी। सतर्क रहें। नदी के किनारे से दूर रहें।'
      : '';

    return {
      step_index: idx,
      hour_offset: s.h,
      timestamp: new Date(Date.now() + s.h * 3_600_000).toISOString(),
      phase_label: isImpact ? 'EVENT' : s.h < -6 ? 'PRE-STORM' : s.h < -3 ? 'STORM BUILD-UP' : 'CRITICAL',
      is_impact_time: isImpact,
      telemetry: {
        rainfall_1h_mm: s.r1,
        rainfall_24h_mm: s.r24,
        rainfall_72h_mm: s.r72,
        soil_saturation_pct: s.sat,
        river_stage_m: s.rv,
        slope_angle_deg: s.slope,
      },
      factor_of_safety: s.fs,
      ml_calibrated_prob: s.prob,
      conformal_lower: s.lo,
      conformal_upper: s.hi,
      ews_tier: s.tier as ReplayFrame['ews_tier'],
      baseline_alert_active: s.base,
      baseline_tier: s.base ? 'EVACUATE' : 'NONE',
      baseline_threshold_rule: s.base
        ? (s.r24 >= 200 ? '24h≥200mm' : s.r1 >= 50 ? '1h≥50mm' : 'Fs≤1.0')
        : '—',
      lead_time_gain_hours: s.base ? 0 : (!s.base && TIER_ORDER[s.tier] >= 1) ? 7.0 : 0,
      analog_match_event: 'Kedarnath 2013 Debris Flow',
      analog_similarity_pct: 72 + Math.round(s.prob * 20),
      explanation_summary: `Soil saturation ${s.sat.toFixed(0)}%, Fs=${s.fs.toFixed(2)}. ${enTier}`,
      time_to_impact_min: Math.max(0, (-s.h) * 60),
      time_to_evacuate_min: 55,
      available_margin_min: margin,
      safe_route_id: severed.length ? 'route_b' : 'route_a',
      safe_route_name: severed.length ? 'Ridge Path B' : 'Highway Route A',
      severed_routes: severed,
      shelter_name: 'Inter College Shelter (Cap: 1200)',
      internet_killed: false,
      active_channels: [
        { channel: 'Cell Broadcast', delivered: true, offline_fallback: false, latency_s: 2.1 },
        { channel: 'SMS / WhatsApp', delivered: true, offline_fallback: false, latency_s: 4.7 },
        { channel: 'IVR Voice Call', delivered: TIER_ORDER[s.tier] >= 2, offline_fallback: false, latency_s: 12.4 },
        { channel: 'Local Siren (LoRa)', delivered: TIER_ORDER[s.tier] >= 2, offline_fallback: true, latency_s: 0.4 },
        { channel: 'VHF Volunteer Radio', delivered: TIER_ORDER[s.tier] >= 2, offline_fallback: true, latency_s: 3.8 },
      ],
      delivery_reach_pct: reach,
      alert_message_en: msgEn,
      alert_message_hi: msgHi,
    };
  });
})();

const BHATWARI_KILL_INTERNET_FRAMES: ReplayFrame[] = BHATWARI_MOCK_FRAMES.map(f => ({
  ...f,
  internet_killed: true,
  active_channels: f.active_channels.map(c => ({
    ...c,
    delivered: c.offline_fallback ? c.delivered : false,
  })),
  delivery_reach_pct: ['EVACUATE', 'WARNING'].includes(f.ews_tier) ? 78.5 : 0,
}));

const MOCK_SCENARIOS: ScenarioInfo[] = [
  {
    id: 'bhatwari_debris_flow_synthetic',
    name: 'Bhatwari Cloudburst & Debris Flow',
    description: '16-step synthetic scenario based on Kedarnath-class event; 12h pre-storm window',
    location: 'Bhatwari, Uttarkashi, Uttarakhand',
    is_synthetic: true,
    step_count: 16,
  },
  {
    id: 'harsil_flash_flood_synthetic',
    name: 'Harsil Glacial Flash Flood',
    description: '10-step synthetic scenario; rapid onset from GLOF precursor',
    location: 'Harsil, Uttarkashi, Uttarakhand',
    is_synthetic: true,
    step_count: 10,
  },
];

// ── API Calls ──────────────────────────────────────────────────────────────

export async function fetchScenarios(): Promise<ScenarioInfo[]> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/replay/scenarios`, { signal: AbortSignal.timeout(4000) });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    console.warn('[replayService] Backend unavailable — using mock scenarios');
    return MOCK_SCENARIOS;
  }
}

export async function runReplay(
  scenarioId: string,
  killInternet: boolean,
  speedMultiplier: number,
): Promise<ReplayResult> {
  try {
    const res = await fetch(`${BASE_URL}/api/v1/replay/run`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario_id: scenarioId, kill_internet: killInternet, speed_multiplier: speedMultiplier }),
      signal: AbortSignal.timeout(10_000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch {
    console.warn('[replayService] Backend unavailable — using mock replay data');
    const frames = killInternet ? BHATWARI_KILL_INTERNET_FRAMES : BHATWARI_MOCK_FRAMES;
    return {
      scenario: {
        id: scenarioId,
        name: 'Bhatwari Cloudburst & Debris Flow',
        description: 'SYNTHETIC EVENT — calibrated from Kedarnath 2013 analog',
        location: 'Bhatwari, Uttarkashi',
        is_synthetic: true,
        data_source_label: 'SYNTHETIC — NOT real sensor data',
      },
      summary: {
        scenario_id: scenarioId,
        total_frames: frames.length,
        ews_first_alert_hour: 'T - 12h',
        baseline_first_alert_hour: 'T - 5h',
        extra_lead_time_hours: 7.0,
        internet_killed: killInternet,
        kill_internet_local_reach_pct: 78.5,
        online_reach_pct: 94.2,
      },
      frames,
    };
  }
}
