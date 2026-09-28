"""Bayes-optimal operational threshold derivation and episode-level early warning evaluation.

Implements:
1. Relative societal cost modeling: cost_miss and cost_false_alarm per village based on
   exposed population, vulnerable demographics, hillslope gradient, stream proximity,
   alert fatigue, and evacuation disruption.
   NOTE: Costs are relative units representing explicit assumptions, not real-world currency.
2. Bayes-optimal alert threshold: p* = cost_false_alarm / (cost_false_alarm + cost_miss),
   with operational clipping and maximum annual alert burden constraints.
3. Multi-tier thresholds (WATCH, WARNING, EVACUATE) derived from the calibration split.
4. Episode-level evaluation: merges consecutive alert hours (gap <= 6h) into coordinated
   emergency episodes, tracking episode POD, FAR, annual burden, and average lead time.
5. Database persistence helper for FastAPI endpoints.
"""

from typing import Dict, Any, List, Optional, Tuple, Union
from datetime import datetime, timezone
import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from ml.models.base_model import get_model, LandslideRiskModel
from ml.models.baseline import RainfallThresholdBaseline


# Default operational clipping bounds
MIN_OPERATIONAL_THRESHOLD = 0.005
MAX_OPERATIONAL_THRESHOLD = 0.250
DEFAULT_MAX_ALERTS_PER_YEAR = 15


def compute_village_costs(village_data: Dict[str, Any]) -> Tuple[float, float]:
    """Compute relative loss/cost metrics for a village under missed detection vs false alarm.
    
    Costs are RELATIVE non-monetary units representing our explicit modeling assumptions:
    - cost_miss: Societal harm/danger of an unannounced translational landslide or debris flow.
      Scales with total population, heavily weights vulnerable demographics (elderly, disabled, children),
      and compounds on steep hillslopes or near active torrent streams.
    - cost_false_alarm: Societal, economic, and compliance disruption of an unnecessary emergency evacuation.
      Scales with population, compound fatigue rate from historical false alerts, and physical terrain disruption.
      
    Returns (cost_miss, cost_false_alarm).
    """
    pop = float(village_data.get("population", 1000))
    vuln_pop = float(village_data.get("vulnerable_population", pop * 0.20))
    slope = float(village_data.get("slope", 30.0))
    dist_stream = float(village_data.get("distance_to_stream", 80.0))
    fatigue_rate = float(village_data.get("historical_alert_fatigue_rate", 0.20))
    disruption_idx = float(village_data.get("evacuation_disruption_index", 0.10))

    # Hillslope hazard amplification: steepness above 25 deg increases slide runout speed
    slope_factor = 1.0 + max(0.0, (slope - 25.0) / 15.0)

    # Fluvial proximity factor: settlements within 100m of drainage channels face direct scour/debris flow
    stream_factor = 1.0 + max(0.0, (100.0 - dist_stream) / 100.0)

    # Relative Cost of Miss (Relative Units)
    cost_miss = (pop * 1.0 + vuln_pop * 2.5) * (1.0 + slope_factor + stream_factor)

    # Relative Cost of False Alarm (Relative Units)
    cost_false_alarm = pop * (0.05 + 0.10 * fatigue_rate + disruption_idx)

    return round(float(cost_miss), 2), round(float(cost_false_alarm), 2)


def compute_bayes_optimal_threshold(
    cost_miss: float,
    cost_false_alarm: float,
    min_thresh: float = MIN_OPERATIONAL_THRESHOLD,
    max_thresh: float = MAX_OPERATIONAL_THRESHOLD,
) -> float:
    """Compute Bayes-optimal decision threshold p* minimizing expected loss.
    
    Threshold rule: Alert if p > cost_false_alarm / (cost_false_alarm + cost_miss).
    Clipped to [min_thresh, max_thresh] to prevent trivial saturation or total silence.
    """
    if (cost_false_alarm + cost_miss) <= 0:
        return 0.020

    raw_threshold = cost_false_alarm / (cost_false_alarm + cost_miss)
    clipped_threshold = float(np.clip(raw_threshold, min_thresh, max_thresh))
    return round(clipped_threshold, 6)


def derive_village_thresholds(
    village_data: Dict[str, Any],
    calib_probs: Optional[np.ndarray] = None,
    max_episodes_per_year: int = DEFAULT_MAX_ALERTS_PER_YEAR,
) -> Dict[str, Any]:
    """Derive full multi-tier Bayes-optimal thresholds and burden constraints for a village."""
    c_miss, c_fa = compute_village_costs(village_data)
    p_star = compute_bayes_optimal_threshold(c_miss, c_fa)

    # Multi-tier operational escalation thresholds
    # WARNING corresponds to the Bayes-optimal staging threshold
    warning_thresh = p_star
    # WATCH corresponds to early advisory (30% lower threshold for heightened monitoring)
    watch_thresh = round(max(MIN_OPERATIONAL_THRESHOLD, p_star * 0.70), 6)
    # EVACUATE corresponds to critical danger (gated by conformal lower bound)
    evac_thresh = round(max(p_star * 3.0, 0.120), 6)

    # Alert Burden Constraint:
    # If historical calibration probabilities produce excessive alert episodes exceeding the annual cap,
    # adjust warning threshold upward to enforce the maximum burden constraint.
    if calib_probs is not None and len(calib_probs) > 0:
        # 1 year in hours = 8760
        alert_mask = (calib_probs >= warning_thresh).astype(int)
        # Approximate episode count on calibration split
        diffs = np.diff(np.pad(alert_mask, (1, 1), 'constant'))
        n_episodes = int(np.sum(diffs == 1))
        
        # If annual alert count exceeds limit, adjust to (1 - max_episodes / total_hours) quantile
        if n_episodes > max_episodes_per_year:
            target_quantile = 100.0 * (1.0 - (max_episodes_per_year / max(len(calib_probs), 1)))
            constrained_thresh = float(np.percentile(calib_probs, target_quantile))
            warning_thresh = round(max(warning_thresh, constrained_thresh), 6)
            watch_thresh = round(max(MIN_OPERATIONAL_THRESHOLD, warning_thresh * 0.70), 6)
            evac_thresh = round(max(warning_thresh * 2.5, evac_thresh), 6)

    return {
        "village_id": village_data.get("village_id", village_data.get("id")),
        "cost_miss": c_miss,
        "cost_false_alarm": c_fa,
        "bayes_optimal_threshold": p_star,
        "watch_threshold": watch_thresh,
        "warning_threshold": warning_thresh,
        "evacuate_threshold": evac_thresh,
        "max_alerts_per_year": max_episodes_per_year,
    }


def merge_consecutive_alert_episodes(
    times: pd.Series,
    alert_flags: np.ndarray,
    max_gap_hours: int = 6,
) -> List[Dict[str, Any]]:
    """Merge consecutive alert hours separated by <= max_gap_hours into coordinated episodes.
    
    Returns list of episode dicts with start, end, and active window_end (end + max_gap_hours).
    """
    times_series = pd.Series(pd.to_datetime(times))
    alert_indices = np.where(np.asarray(alert_flags) == 1)[0]
    if len(alert_indices) == 0:
        return []

    alert_times = times_series.iloc[alert_indices].sort_values().tolist()
    episodes = []

    cur_start = alert_times[0]
    cur_end = alert_times[0]

    for t in alert_times[1:]:
        gap_hours = (t - cur_end).total_seconds() / 3600.0
        if gap_hours <= (max_gap_hours + 1e-4):
            cur_end = t
        else:
            episodes.append({
                "start": cur_start,
                "end": cur_end,
                "window_end": cur_end + pd.Timedelta(hours=max_gap_hours),
            })
            cur_start = t
            cur_end = t

    episodes.append({
        "start": cur_start,
        "end": cur_end,
        "window_end": cur_end + pd.Timedelta(hours=max_gap_hours),
    })

    return episodes


def _extract_ground_truth_events(village_df: pd.DataFrame, target_col: str = "landslide_within_6h") -> List[Dict[str, Any]]:
    """Identify contiguous 6-hour failure event windows in village ground truth."""
    sub = village_df.sort_values("time").reset_index(drop=True)
    pos_idx = sub[sub[target_col] == 1].index.tolist()
    events = []
    if not pos_idx:
        return events

    cur_block = [pos_idx[0]]
    for idx in pos_idx[1:]:
        if idx == cur_block[-1] + 1:
            cur_block.append(idx)
        else:
            events.append({
                "start": sub.loc[cur_block[0], "time"],
                "end": sub.loc[cur_block[-1], "time"],
            })
            cur_block = [idx]

    events.append({
        "start": sub.loc[cur_block[0], "time"],
        "end": sub.loc[cur_block[-1], "time"],
    })
    return events


def evaluate_episode_level(
    test_df: pd.DataFrame,
    village_thresholds_map: Optional[Dict[str, Dict[str, float]]] = None,
    global_warning_threshold: float = 0.018041,
    max_gap_hours: int = 6,
    base_model: Optional[LandslideRiskModel] = None,
) -> Dict[str, Any]:
    """Execute episode-level evaluation comparing Global vs Per-Village vs Baseline strategies on test split.
    
    Evaluates:
    (a) Global threshold: p >= 0.018041
    (b) Per-village Bayes-optimal thresholds
    (c) Rainfall Intensity-Duration baseline
    """
    model = base_model or get_model()
    baseline = RainfallThresholdBaseline()

    df = test_df.copy()
    df["time"] = pd.to_datetime(df["time"])
    villages = df["village_id"].unique().tolist()
    n_villages = len(villages)
    n_years = 1.0  # 2023 holdout test year

    # Precompute probabilities and baseline alerts
    probs = model.predict_proba(df)
    df["cal_prob"] = probs
    df["baseline_alert"] = baseline.predict(df)

    # Build per-village thresholds if not provided
    if village_thresholds_map is None:
        village_thresholds_map = {}
        for vil in villages:
            v_sub = df[df["village_id"] == vil]
            slope = float(v_sub["slope"].mean())
            dist = float(v_sub["distance_to_stream"].mean())
            elev = float(v_sub["elevation"].mean())
            # Plausible demographic defaults based on settlement size
            pop = 800 if elev > 2000 else 1800
            vuln = int(pop * 0.22)
            th_info = derive_village_thresholds({
                "village_id": vil,
                "population": pop,
                "vulnerable_population": vuln,
                "slope": slope,
                "distance_to_stream": dist,
                "evacuation_disruption_index": 0.12 if elev > 2000 else 0.08,
            })
            village_thresholds_map[vil] = th_info

    strategies = {
        "global_threshold": {
            "label": f"Global Threshold (p >= {global_warning_threshold:.4f})",
            "alert_fn": lambda sub, vil: (sub["cal_prob"] >= global_warning_threshold).astype(int),
        },
        "per_village_bayes": {
            "label": "Per-Village Bayes-Optimal",
            "alert_fn": lambda sub, vil: (sub["cal_prob"] >= village_thresholds_map[vil]["warning_threshold"]).astype(int),
        },
        "rainfall_baseline": {
            "label": "Rainfall I-D Baseline",
            "alert_fn": lambda sub, vil: sub["baseline_alert"].values,
        },
    }

    results = {}

    for strat_key, strat in strategies.items():
        total_episodes = 0
        total_gt_events = 0
        detected_gt_events = 0
        tp_episodes = 0
        fp_episodes = 0
        lead_times = []

        for vil in villages:
            v_df = df[df["village_id"] == vil].copy().reset_index(drop=True)
            alerts = strat["alert_fn"](v_df, vil)
            episodes = merge_consecutive_alert_episodes(v_df["time"], alerts, max_gap_hours=max_gap_hours)
            gt_events = _extract_ground_truth_events(v_df)

            total_episodes += len(episodes)
            total_gt_events += len(gt_events)

            # Check alert episode outcome (hit vs false alarm)
            for ep in episodes:
                hit = False
                for gt in gt_events:
                    if ep["start"] <= gt["end"] and gt["start"] <= ep["window_end"]:
                        hit = True
                        break
                if hit:
                    tp_episodes += 1
                else:
                    fp_episodes += 1

            # Check ground truth event detection (POD & lead time)
            for gt in gt_events:
                detected = False
                earliest_alert = None
                for ep in episodes:
                    if ep["start"] <= gt["end"] and gt["start"] <= ep["window_end"]:
                        detected = True
                        if earliest_alert is None or ep["start"] < earliest_alert:
                            earliest_alert = ep["start"]
                if detected and earliest_alert is not None:
                    detected_gt_events += 1
                    lt_hours = (gt["start"] - earliest_alert).total_seconds() / 3600.0
                    lead_times.append(max(0.0, lt_hours))

        pod = (detected_gt_events / total_gt_events) if total_gt_events > 0 else 0.0
        far = (fp_episodes / total_episodes) if total_episodes > 0 else 0.0
        csi_denom = detected_gt_events + fp_episodes + (total_gt_events - detected_gt_events)
        csi = (detected_gt_events / csi_denom) if csi_denom > 0 else 0.0
        alerts_per_vil_year = total_episodes / (n_villages * n_years)
        avg_lead_time = float(np.mean(lead_times)) if lead_times else 0.0

        results[strat_key] = {
            "strategy": strat["label"],
            "total_episodes": total_episodes,
            "episodes_per_village_year": round(alerts_per_vil_year, 1),
            "detected_events": detected_gt_events,
            "total_ground_truth_events": total_gt_events,
            "episode_pod": round(float(pod), 4),
            "episode_far": round(float(far), 4),
            "episode_csi": round(float(csi), 4),
            "avg_lead_time_hours": round(avg_lead_time, 2),
        }

    return {
        "episode_evaluation": results,
        "village_thresholds": village_thresholds_map,
    }


def init_village_thresholds(db: Session, force_recompute: bool = False) -> List[Any]:
    """Seed or synchronize Bayes-optimal threshold entries in the database for all registered villages."""
    from backend.app.db.models import Village, VillageThreshold, Recipient

    villages = db.query(Village).all()
    created_or_updated = []

    for v in villages:
        existing = db.query(VillageThreshold).filter(VillageThreshold.village_id == v.id).first()
        if existing and not force_recompute:
            created_or_updated.append(existing)
            continue

        # Fetch demographics and terrain
        recipients = db.query(Recipient).filter(Recipient.village_id == v.id).all()
        vuln_count = sum(1 for r in recipients if r.vulnerable_flag)
        if vuln_count == 0:
            vuln_count = max(1, int(v.population * 0.18))

        # Terrain approximation based on elevation & valley
        slope = 36.0 if v.elevation > 2000 else 24.0
        dist_stream = 40.0 if v.elevation < 1500 else 85.0
        disruption = 0.14 if v.elevation > 2200 else 0.08

        thresholds_data = derive_village_thresholds({
            "village_id": v.id,
            "population": v.population,
            "vulnerable_population": vuln_count,
            "slope": slope,
            "distance_to_stream": dist_stream,
            "evacuation_disruption_index": disruption,
        })

        if existing:
            existing.cost_miss = thresholds_data["cost_miss"]
            existing.cost_false_alarm = thresholds_data["cost_false_alarm"]
            existing.bayes_optimal_threshold = thresholds_data["bayes_optimal_threshold"]
            existing.watch_threshold = thresholds_data["watch_threshold"]
            existing.warning_threshold = thresholds_data["warning_threshold"]
            existing.evacuate_threshold = thresholds_data["evacuate_threshold"]
            existing.max_alerts_per_year = thresholds_data["max_alerts_per_year"]
            existing.last_modified_by = "system"
            existing.last_modified_at = datetime.now(timezone.utc)
            record = existing
        else:
            record = VillageThreshold(
                village_id=v.id,
                cost_miss=thresholds_data["cost_miss"],
                cost_false_alarm=thresholds_data["cost_false_alarm"],
                bayes_optimal_threshold=thresholds_data["bayes_optimal_threshold"],
                watch_threshold=thresholds_data["watch_threshold"],
                warning_threshold=thresholds_data["warning_threshold"],
                evacuate_threshold=thresholds_data["evacuate_threshold"],
                max_alerts_per_year=thresholds_data["max_alerts_per_year"],
                last_modified_by="system",
                last_modified_at=datetime.now(timezone.utc),
                change_reason="Initial Bayes-optimal calibration seed",
                audit_log=[{
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "user": "system",
                    "action": "initial_seed",
                    "thresholds": {
                        "watch": thresholds_data["watch_threshold"],
                        "warning": thresholds_data["warning_threshold"],
                        "evacuate": thresholds_data["evacuate_threshold"],
                    },
                }],
            )
            db.add(record)

        created_or_updated.append(record)

    db.commit()
    print(f"[+] Synced Bayes-optimal thresholds for {len(created_or_updated)} villages in database.")
    return created_or_updated
