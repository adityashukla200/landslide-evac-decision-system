"""Script generating publication-grade FS vs. Cumulative Rainfall curves across 3 slope regimes."""

import sys
from pathlib import Path
from typing import Optional
import numpy as np
import matplotlib.pyplot as plt

# Ensure root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from ml.physics.slope_stability import compute_infinite_slope_fs

ROOT_DIR = Path(__file__).resolve().parent.parent.parent


def plot_factor_of_safety_curves(output_path: Optional[Path] = None) -> Path:
    """Generate and save FS vs rainfall response curves for 3 hillslope angles."""
    save_file = output_path or (ROOT_DIR / "docs" / "fs_vs_rainfall.png")
    save_file.parent.mkdir(parents=True, exist_ok=True)

    rainfall_range = np.linspace(0.0, 180.0, 200)  # 0 to 180 mm
    slopes = [20.0, 32.0, 44.0]
    labels = ["Gentle Slope (20°) - Valley Plain", "Moderate Slope (32°) - Mid-Hillslope", "Steep Slope (44°) - Gorge Wall"]
    colors = ["#10b981", "#f59e0b", "#ef4444"]

    # Baseline geotechnical properties
    cohesion = 12.0  # kPa
    friction_angle = 32.0  # deg
    soil_depth = 1.8  # m
    porosity = 0.38
    initial_moisture = 0.30

    plt.figure(figsize=(10, 6), dpi=300)

    for slope, label, color in zip(slopes, labels, colors):
        # Infiltration to saturation conversion
        soil_capacity_mm = soil_depth * porosity * 1000.0
        saturation = np.clip(initial_moisture + (rainfall_range / soil_capacity_mm), 0.0, 1.0)

        fs_values = compute_infinite_slope_fs(
            slope_deg=slope,
            cohesion_kpa=cohesion,
            friction_angle_deg=friction_angle,
            soil_depth_m=soil_depth,
            saturation_ratio=saturation,
            gamma_kn_m3=18.5,
            gamma_w_kn_m3=9.81,
        )

        plt.plot(rainfall_range, fs_values, label=label, color=color, linewidth=2.5)

    # Highlight threshold lines
    plt.axhline(y=1.0, color="#b91c1c", linestyle="--", linewidth=1.8, label="Failure Threshold (FS = 1.0)")
    plt.axhline(y=1.3, color="#047857", linestyle=":", linewidth=1.5, label="Safe Threshold (FS = 1.3)")

    plt.title("Infinite-Slope Factor of Safety vs. Cumulative Rainfall (Uttarkashi Regolith)", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Cumulative Rainfall Infiltration (mm)", fontsize=11)
    plt.ylabel("Factor of Safety (FS)", fontsize=11)
    plt.xlim(0, 180)
    plt.ylim(0.4, 2.8)
    plt.grid(True, linestyle="--", alpha=0.5)
    plt.legend(loc="upper right", framealpha=0.95, fontsize=10)
    plt.tight_layout()

    plt.savefig(save_file)
    plt.close()
    print(f"[+] Saved FS vs rainfall curve figure to {save_file}")
    return save_file


if __name__ == "__main__":
    from typing import Optional
    plot_factor_of_safety_curves()
