"""Reproducible end-to-end training pipeline for the physics-informed early warning model.

Executes:
1. Physics pretraining on 120,000 synthetic geotechnical scenarios (physics_synthetic.parquet).
2. Time-ordered fine-tuning (2019-2021) and probability calibration (2022) with factor_of_safety.
3. Model and calibrator serialization to ml/models/saved/landslide_xgboost.joblib.
4. Strict spatial + temporal cross-validation with matched operating points and reliability curves.
"""

import sys
import time
from pathlib import Path
import pandas as pd

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml.physics.scenario_generator import save_physics_dataset
from ml.data.synthetic import run_pipeline as run_synthetic_pipeline
from ml.models.base_model import LandslideRiskModel, DEFAULT_MODEL_PATH
from ml.evaluate import run_evaluation

ROOT_DIR = Path(__file__).resolve().parent.parent
PHYSICS_DATA_PATH = ROOT_DIR / "data" / "processed" / "physics_synthetic.parquet"
FEATURE_TABLE_PATH = ROOT_DIR / "data" / "processed" / "feature_table.parquet"


def main():
    print("=" * 70)
    print("  EARLY WARNING SYSTEM: PHYSICS-PRETRAINED ML TRAINING PIPELINE")
    print("=" * 70)
    start_total = time.perf_counter()

    # Step 1: Ensure physics scenarios exist
    if not PHYSICS_DATA_PATH.exists():
        print("[Step 1/4] Physics dataset not found. Generating 120,000 scenarios...")
        save_physics_dataset(output_path=PHYSICS_DATA_PATH, n_samples=120_000)
    else:
        print(f"[Step 1/4] Physics dataset found at {PHYSICS_DATA_PATH}")

    # Step 2: Ensure village feature table exists
    if not FEATURE_TABLE_PATH.exists():
        print("[Step 2/4] Feature table not found. Generating 5-year village dataset...")
        run_synthetic_pipeline()
    else:
        print(f"[Step 2/4] Village feature table found at {FEATURE_TABLE_PATH}")

    # Load data
    physics_df = pd.read_parquet(PHYSICS_DATA_PATH)
    village_df = pd.read_parquet(FEATURE_TABLE_PATH)
    village_df["time"] = pd.to_datetime(village_df["time"])
    village_df["year"] = village_df["time"].dt.year

    holdout_villages = ["VIL_UTK_21", "VIL_UTK_22", "VIL_UTK_23", "VIL_UTK_24", "VIL_UTK_25"]
    train_mask = (~village_df["village_id"].isin(holdout_villages)) & (village_df["year"].isin([2019, 2020, 2021]))
    calib_mask = (~village_df["village_id"].isin(holdout_villages)) & (village_df["year"] == 2022)

    train_df = village_df[train_mask].reset_index(drop=True)
    calib_df = village_df[calib_mask].reset_index(drop=True)

    # Step 3: Initialize Model & Pretrain on Physics
    print("\n[Step 3/4] Pretraining LandslideRiskModel on geotechnical physics scenarios...")
    model = LandslideRiskModel(
        n_estimators=150,
        max_depth=5,
        learning_rate=0.06,
        subsample=0.85,
        colsample_bytree=0.85,
        random_state=42,
    )
    model.pretrain_on_physics(physics_df)

    # Fine-tune on 2019-2021 and calibrate on 2022
    print("\n[Step 3/4 - Continued] Fine-tuning model on 2019-2021 records and calibrating on 2022...")
    model.fine_tune(train_df, calib_df=calib_df)

    # Save model artifact
    save_path = model.save(DEFAULT_MODEL_PATH)
    print(f"[+] Model artifact successfully persisted to {save_path}")

    # Step 4: Run Strict Spatial + Temporal Cross-Validation
    print("\n[Step 4/4] Executing strict Spatial + Temporal Cross-Validation...")
    results = run_evaluation(feature_table_path=FEATURE_TABLE_PATH, save_docs=True)

    cal = results["calibration"]
    op_pod = results["matched_operating_points"]["matched_pod_operating_point"]

    elapsed = time.perf_counter() - start_total
    print("\n" + "=" * 70)
    print(f"  TRAINING & CALIBRATION PIPELINE COMPLETE (Elapsed: {elapsed:.2f}s)")
    print(f"  Model:       {save_path}")
    print(f"  Results:     docs/RESULTS.md and docs/evaluation_results.json")
    print(f"  Calibration: Method={cal['chosen_method']} | ECE={cal['test_calibrated_ece']:.6f} | BSS={cal['brier_skill_score_calibrated']:+.4f}")
    print(f"  Matched POD: POD={op_pod['model_pod']:.2%} | FAR={op_pod['model_far']:.2%} | CSI={op_pod['model_csi']:.4f}")
    print("=" * 70)


if __name__ == "__main__":
    main()
