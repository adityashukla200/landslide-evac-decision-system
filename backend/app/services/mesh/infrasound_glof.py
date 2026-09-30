"""Acoustic / Geophone GLOF & Debris Flow Infrasound Detection Service.

Processes SM-24 class geophone and MEMS infrasound acoustic streams in the 1-30 Hz band.
Provides 15-30 minute early warning of glacial lake outburst flood breaches
and hyper-concentrated debris flows before surface stage rise occurs downstream.
"""

import math
from typing import List, Dict, Any
from datetime import datetime, timezone


class InfrasoundGLOFDetector:
    """TinyML / DSP engine for low-frequency acoustic surge detection."""

    # Infrasound characteristic band for Himalayan GLOFs / turbulent mass wasting
    GLOF_BAND_MIN_HZ = 1.5
    GLOF_BAND_MAX_HZ = 12.0
    SURGE_ENERGY_THRESHOLD = 0.55  # 55% spectral power concentrated in 1.5-12 Hz
    PRESSURE_SURGE_THRESHOLD_PA = 2.5  # Pascals peak acoustic pressure

    def __init__(self):
        # Rolling detection window per station to prevent single-burst false alarms
        self.rolling_windows: Dict[str, List[float]] = {}

    def analyze_spectrum(
        self,
        station_id: str,
        village_id: str,
        frequencies_hz: List[float],
        spectral_amplitudes_db: List[float],
        peak_amplitude_pa: float,
    ) -> Dict[str, Any]:
        """Analyzes frequency power spectrum and computes infrasonic surge ratio."""
        if not frequencies_hz or len(frequencies_hz) != len(spectral_amplitudes_db):
            return {
                "station_id": station_id,
                "village_id": village_id,
                "dominant_frequency_hz": 0.0,
                "infrasound_energy_ratio": 0.0,
                "anomaly_score": 0.0,
                "glof_rumble_detected": False,
                "confidence": 0.0,
                "estimated_lead_time_minutes": 0,
                "action_taken": "INVALID_INPUT",
            }

        # Convert dB to linear power: P = 10^(dB/10)
        linear_powers = [10.0 ** (db / 10.0) for db in spectral_amplitudes_db]
        total_power = sum(linear_powers) + 1e-9

        # Find dominant peak frequency
        max_idx = linear_powers.index(max(linear_powers))
        dominant_freq = frequencies_hz[max_idx]

        # Calculate energy in GLOF infrasound band (1.5 - 12 Hz)
        glof_band_power = 0.0
        for freq, power in zip(frequencies_hz, linear_powers):
            if self.GLOF_BAND_MIN_HZ <= freq <= self.GLOF_BAND_MAX_HZ:
                glof_band_power += power

        energy_ratio = min(1.0, glof_band_power / total_power)

        # Multi-factor anomaly score
        pressure_factor = min(1.0, peak_amplitude_pa / 5.0)
        anomaly_score = round(0.65 * energy_ratio + 0.35 * pressure_factor, 3)

        # Rolling history buffer (keep last 5 windows)
        if station_id not in self.rolling_windows:
            self.rolling_windows[station_id] = []
        self.rolling_windows[station_id].append(anomaly_score)
        if len(self.rolling_windows[station_id]) > 5:
            self.rolling_windows[station_id].pop(0)

        avg_rolling_score = sum(self.rolling_windows[station_id]) / len(self.rolling_windows[station_id])

        # Detection logic: persistent elevated infrasound energy and high pressure
        is_glof = (
            energy_ratio >= self.SURGE_ENERGY_THRESHOLD
            and peak_amplitude_pa >= self.PRESSURE_SURGE_THRESHOLD_PA
            and avg_rolling_score >= 0.50
        )

        confidence = round(min(0.98, max(0.20, anomaly_score * 1.1)), 2)

        # Estimated lead time in Himalayan valleys (typical distance 10-25 km at 8-12 m/s debris surge)
        estimated_lead_time = 25 if is_glof else 0

        action = "NORMAL_MONITORING"
        if is_glof:
            action = "TRIGGER_EDGE_SIREN_AND_MESH_BROADCAST"
        elif anomaly_score >= 0.40:
            action = "ELEVATED_WATCH_PRE_ALARM"

        return {
            "station_id": station_id,
            "village_id": village_id,
            "dominant_frequency_hz": round(dominant_freq, 2),
            "infrasound_energy_ratio": round(energy_ratio, 3),
            "anomaly_score": anomaly_score,
            "glof_rumble_detected": is_glof,
            "confidence": confidence,
            "estimated_lead_time_minutes": estimated_lead_time,
            "action_taken": action,
        }
