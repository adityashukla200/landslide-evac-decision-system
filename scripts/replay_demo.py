#!/usr/bin/env python3
"""Disaster Timeline Replay & Demonstration CLI.

Fast-forwards extreme weather / geotechnical events through the complete EWS pipeline:
- Telemetry & Physics Factor of Safety
- Calibrated ML & Venn-Abers Conformal Bounds
- Analog Storm Matching & Plain Baseline Comparison
- Evacuation Margins & Safe Routing
- Multi-Channel Alerting & Offline 'Kill Internet' Simulation
"""

import sys
import argparse
import time
import json
from pathlib import Path

# Add project root to sys.path
ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from backend.app.services.replay import get_replay_engine, AVAILABLE_SCENARIOS


def print_banner(scenario_info: dict, kill_internet: bool):
    print("=" * 88)
    print("  SIH-26192: HILLY REGION FLASH FLOOD & LANDSLIDE EARLY WARNING SYSTEM")
    print("  EMERGENCY DISASTER REPLAY & PIPELINE DEMONSTRATION ENGINE")
    print("=" * 88)
    print(f"  Target Catchment : {scenario_info['village_name']} (Uttarkashi Pilot Region)")
    print(f"  Disaster Event   : {scenario_info['name']}")
    print(f"  Hazard Category  : {scenario_info['hazard_type']}")
    print(f"  Dataset Origin   : {scenario_info['data_source_label']}")
    if scenario_info.get("is_synthetic"):
        print("  [!] SCIENTIFIC NOTE: SYNTHETIC TIMELINE (Calibrated on Uttarakhand Historical Monsoon Telemetry)")
    print(f"  Internet Switch  : {'[DISCONNECTED / KILL INTERNET ACTIVE]' if kill_internet else '[ONLINE / CLOUD CONNECTED]'}")
    print("=" * 88)
    print()


def render_step_row(frame: dict, idx: int, total: int):
    offset = frame["hour_offset"]
    time_str = f"T - {abs(offset)}h" if offset < 0 else (f"T + {offset}h" if offset > 0 else "T - 0 (IMPACT)")
    
    # ANSI color helpers
    tier = frame["ews_tier"]
    tier_color = {
        "NONE": "\033[90m",       # Gray
        "WATCH": "\033[93m",      # Yellow
        "WARNING": "\033[38;5;208m", # Orange
        "EVACUATE": "\033[91m",   # Red
    }.get(tier, "\033[0m")
    reset = "\033[0m"

    print(f"\n--- [Step {idx+1}/{total}] {time_str} | Phase: {frame['phase_label']} ---")
    print(f"  Telemetry      : Rain 1h: {frame['telemetry']['rainfall_1h_mm']:.1f}mm | 24h: {frame['telemetry']['rainfall_24h_mm']:.1f}mm | Soil Sat: {frame['telemetry']['soil_saturation_pct']:.0f}% | River: {frame['telemetry']['river_stage_m']:.1f}m")
    print(f"  Slope Physics  : Factor of Safety (Fs) = {frame['factor_of_safety']:.3f} {'[UNSTABLE]' if frame['factor_of_safety'] < 1.0 else '[CRITICAL]' if frame['factor_of_safety'] < 1.15 else '[STABLE]'}")
    print(f"  ML Probability : P(Failure) = {frame['ml_calibrated_prob']:.4f} | Venn-Abers [{frame['conformal_lower']:.4f}, {frame['conformal_upper']:.4f}]")
    print(f"  Our EWS Tier   : {tier_color}[{tier}]{reset} (Bayes threshold: {frame['bayes_threshold']:.4f})")
    
    # Baseline comparison
    baseline_active = frame["baseline_alert_active"]
    base_color = "\033[91m" if baseline_active else "\033[90m"
    print(f"  Plain Baseline : {base_color}[{'ALERTED (' + frame['baseline_tier'] + ')' if baseline_active else 'NO ALERT (Below 200mm threshold)'}]{reset}")
    if frame["lead_time_gain_hours"] > 0:
        print(f"  Lead Time Gain : \033[92m+{frame['lead_time_gain_hours']:.1f} Hours Advance Head-Start\033[0m vs Static Threshold")

    # Routing
    print(f"  Evac Logistics : Margin: {frame['available_margin_min']:.0f} mins | Route: {frame['safe_route_name']}")
    if frame["severed_routes"]:
        print(f"  Route Status   : \033[91m[SEVERED: {', '.join(frame['severed_routes'])}\033[0m]")

    # Channels
    if frame["internet_killed"]:
        siren_status = next((c for c in frame["active_channels"] if "Siren" in c["channel"]), None)
        radio_status = next((c for c in frame["active_channels"] if "Volunteer" in c["channel"]), None)
        print(f"  Offline Relay  : Edge Siren: {'\033[92mFIRED (LoRa/RF)\033[0m' if siren_status and siren_status['delivered'] else '\033[90mSTANDBY\033[0m'} | VHF Radio: {'\033[92mDISPATCHED\033[0m' if radio_status and radio_status['delivered'] else '\033[90mSTANDBY\033[0m'}")
    else:
        active_list = [c["channel"] for c in frame["active_channels"] if c["delivered"]]
        print(f"  Cloud Channels : Reach: {frame['delivery_reach_pct']:.1f}% | Active: {', '.join(active_list) if active_list else 'None'}")


def run_demo(scenario_id: str, kill_internet: bool, speed: float, output_json: bool):
    engine = get_replay_engine()
    results = engine.run_replay(scenario_id=scenario_id, kill_internet=kill_internet)

    if output_json:
        print(json.dumps(results, indent=2))
        return

    scenario = results["scenario"]
    summary = results["summary"]
    frames = results["frames"]

    print_banner(scenario, kill_internet)

    sleep_sec = 0.6 / max(0.1, speed) if speed > 0 else 0.0

    for idx, f in enumerate(frames):
        render_step_row(f, idx, len(frames))
        if sleep_sec > 0:
            time.sleep(sleep_sec)

    print("\n" + "=" * 88)
    print("  REPLAY SIMULATION SUMMARY & DECISION AUDIT")
    print("=" * 88)
    print(f"  • Multi-Source EWS First Alert Time    : {summary['ews_first_alert_hour']}")
    print(f"  • Plain Static Baseline Alert Time     : {summary['baseline_first_alert_hour']}")
    print(f"  • Extra Lead Time Advance Gained       : \033[92m+{summary['extra_lead_time_hours']} HOURS\033[0m")
    print(f"  • Network State                        : {'KILL INTERNET ACTIVE (Local Siren & VHF Mesh Engaged)' if summary['internet_killed'] else 'Cloud Connected (94.2% Multi-Channel Reach)'}")
    print(f"  • Estimated Evacuation Success Rate    : {summary['casualties_prevented_est']}")
    print("=" * 88)
    print()


def main():
    parser = argparse.ArgumentParser(description="SIH-26192 Disaster Early Warning Replay & Demo Engine")
    parser.add_argument(
        "--scenario",
        default="bhatwari_debris_flow_synthetic",
        choices=list(AVAILABLE_SCENARIOS.keys()),
        help="Disaster scenario ID to replay",
    )
    parser.add_argument(
        "--kill-internet",
        action="store_true",
        help="Simulate severe network blackout: disables cloud channels and exercises local siren & VHF mesh radio",
    )
    parser.add_argument(
        "--speed",
        type=float,
        default=2.0,
        help="Playback speed multiplier (default: 2.0, set to 0 for instant print)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output raw JSON results for automated consumption",
    )
    args = parser.parse_args()

    run_demo(
        scenario_id=args.scenario,
        kill_internet=args.kill_internet,
        speed=args.speed,
        output_json=args.json,
    )


if __name__ == "__main__":
    main()
