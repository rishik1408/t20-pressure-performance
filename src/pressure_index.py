"""
Stage 3: Phase-Normalized Dynamic Pressure Index (P-NPI)
Computes the exact Phase-Normalized Pressure Index matching the prototype:
  - Phase-Normalized Wicket Crisis (0-40 pts): Powerplay 15/2 is recognized as high crisis.
  - Dynamic Run Rate Pressure (0-40 pts): RRR vs CRR chase dynamics & 1st inn benchmark deficits.
  - Baseline tension (15 pts).
"""

import numpy as np
import pandas as pd


def compute_pressure_index(bbb):
    """
    Compute Phase-Normalized Pressure Index (P-NPI) (0-100) for every delivery.
    Matches the exact calibrated formula from the benchmark prototype.
    """
    print("Stage 3: Computing Phase-Normalized Pressure Index (P-NPI)...")

    ov = bbb['overid'].values
    wb = bbb['wickets_before'].values
    inn = bbb['innings'].values

    # Phase-Normalized Wicket Crisis (0-40 pts)
    pp_w = np.minimum(40.0, wb * 20.0)
    mid_w = np.minimum(40.0, (wb / 5.0) * 40.0)
    death_w = np.minimum(40.0, (wb / 7.0) * 40.0)
    w_score = np.where(ov <= 6, pp_w, np.where(ov <= 15, mid_w, death_w))

    # Dynamic Run Rate Pressure (0-40 pts)
    rrr = bbb['rrr_before'].fillna(8.0).values
    crr = bbb['crr_before'].values

    gap = np.maximum(0.0, rrr - crr)
    rr_2nd = np.minimum(40.0, gap * 8.0)

    target_crr = np.where(ov <= 6, 8.5, np.where(ov <= 15, 8.0, 10.5))
    deficit = np.maximum(0.0, target_crr - crr)
    rr_1st = np.minimum(25.0, deficit * 6.0)

    rr_score = np.where(inn == 2, rr_2nd, rr_1st)

    # Baseline tension 15.0 pts
    pi = np.minimum(100.0, w_score + rr_score + 15.0)

    bbb = bbb.copy()
    bbb['pressure_wk'] = w_score
    bbb['pressure_rr'] = rr_score
    bbb['pressure_index'] = pi

    # Flag high and low pressure deliveries
    bbb['is_high_pressure'] = (pi >= 50.0).astype(int)
    bbb['is_hp'] = (pi >= 50.0).astype(int)
    bbb['is_low_pressure'] = (pi < 35.0).astype(int)
    bbb['is_lp'] = (pi < 35.0).astype(int)

    hp_count = (pi >= 50.0).sum()
    lp_count = (pi < 35.0).sum()
    print(f"  P-NPI stats: mean={pi.mean():.1f}, median={np.median(pi):.1f}, std={pi.std():.1f}")
    print(f"  High Pressure Deliveries (PI >= 50): {hp_count} ({100*hp_count/len(pi):.1f}%)")
    print(f"  Low Pressure Deliveries  (PI < 35):  {lp_count} ({100*lp_count/len(pi):.1f}%)")

    return bbb
