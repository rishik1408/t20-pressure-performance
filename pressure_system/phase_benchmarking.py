"""
Phase-Relative Benchmarking (The Top/Middle Order Equalizer)
Computes:
  1. Entry-Point Baseline: Tracks match state (score, wickets, over, WP) at batter's entry.
  2. Top-Order Collapse Rescue & Anchoring Pressure Index (API).
  3. Phase-Specific Expected Runs (xRuns) across Powerplay, Middle, and Death.
  4. Phase-Relative Value Added (PRVA) to equalize top/middle order vs finishers.
"""

import numpy as np
import pandas as pd


def compute_phase_xruns(bbb):
    """
    Compute expected runs (xRuns) for every delivery based on:
      - Phase: Powerplay (1-6), Middle (7-15), Death (16-20)
      - Wickets in hand (10 - wickets_before)
      - Innings (1 or 2)
    Returns enriched DataFrame with xruns and xruns_delta (runs - xruns).
    """
    print("  Computing Phase-Specific Expected Runs (xRuns)...")

    # Group wickets into brackets to avoid overfitting:
    # 0-1 wickets down, 2-3 wickets down, 4-5 wickets down, 6+ wickets down
    w_bucket = np.where(bbb['wickets_before'] <= 1, '0-1',
               np.where(bbb['wickets_before'] <= 3, '2-3',
               np.where(bbb['wickets_before'] <= 5, '4-5', '6+')))

    bbb['w_bucket'] = w_bucket

    # Historical expected runs off the bat for legal deliveries
    legal = bbb[bbb['is_legal_delivery'] == 1]
    baseline_table = legal.groupby(['phase', 'w_bucket', 'innings'])['runs'].agg(['mean', 'count']).reset_index()
    baseline_table.rename(columns={'mean': 'xruns_baseline'}, inplace=True)

    # Merge back to all deliveries
    bbb = bbb.merge(
        baseline_table[['phase', 'w_bucket', 'innings', 'xruns_baseline']],
        on=['phase', 'w_bucket', 'innings'],
        how='left'
    )
    bbb['xruns'] = bbb['xruns_baseline'].fillna(1.25)
    bbb['xruns_delta'] = np.where(bbb['is_legal_delivery'] == 1, bbb['runs'] - bbb['xruns'], 0.0)

    # For bowlers: runs_prevented_delta = (xruns + expected_extras) - total_off_ball
    bbb['bowling_xruns_saved'] = bbb['xruns'] - bbb['total_off_ball']

    print(f"  xRuns computed. Global mean xRuns: {bbb['xruns'].mean():.3f} runs/ball")
    return bbb


def compute_anchoring_and_entry_baselines(bbb):
    """
    Compute entry-point baselines and Anchoring Pressure Index (API) for each batter.
    Identifies top-order collapse scenarios and measures rebuilding execution.
    """
    print("  Computing Entry-Point Baselines and Anchoring Pressure Index...")

    # Extract all batter stints (crease occupancy from entry to exit)
    striker_app = bbb[['match_id', 'innings', 'innings_ball_num', 'overid', 'total_runs_before',
                       'wickets_before', 'wp_before', 'striker_id', 'striker_name']].rename(
        columns={'striker_id': 'player_id', 'striker_name': 'player_name'})

    non_striker_app = bbb[['match_id', 'innings', 'innings_ball_num', 'overid', 'total_runs_before',
                           'wickets_before', 'wp_before', 'non_striker_id', 'non_striker_name']].rename(
        columns={'non_striker_id': 'player_id', 'non_striker_name': 'player_name'})

    appearances = pd.concat([striker_app, non_striker_app]).sort_values(['match_id', 'innings', 'innings_ball_num'])

    # Aggregate to stint level
    stints = appearances.groupby(['match_id', 'innings', 'player_id', 'player_name']).agg(
        entry_ball=('innings_ball_num', 'min'),
        exit_ball=('innings_ball_num', 'max'),
        entry_over=('overid', 'min'),
        exit_over=('overid', 'max'),
        entry_runs=('total_runs_before', 'min'),
        exit_runs=('total_runs_before', 'max'),
        entry_wkts=('wickets_before', 'min'),
        exit_wkts=('wickets_before', 'max'),
        entry_wp=('wp_before', 'first'),
        exit_wp=('wp_before', 'last'),
        crease_balls=('innings_ball_num', 'count')
    ).reset_index()

    # Personal runs and balls faced per stint
    personal = bbb[bbb['is_legal_delivery'] == 1].groupby(['match_id', 'innings', 'striker_id']).agg(
        personal_runs=('runs', 'sum'),
        balls_faced=('runs', 'count')
    ).reset_index().rename(columns={'striker_id': 'player_id'})

    stints = stints.merge(personal, on=['match_id', 'innings', 'player_id'], how='left').fillna(0)

    # Rebuild & Anchoring metrics
    stints['team_runs_added'] = stints['exit_runs'] - stints['entry_runs']
    stints['wp_tenure_shift'] = stints['exit_wp'] - stints['entry_wp']

    # Definition of a Collapse Entry:
    # 1. Powerplay collapse: entered in overs 1-6 with 2+ wickets down
    # 2. Severe early collapse: entered in overs 1-4 with 1+ wicket down and <= 20 runs
    # 3. Middle order collapse: entered in overs 7-10 with 4+ wickets down
    is_pp_collapse = (stints['entry_over'] <= 6) & (stints['entry_wkts'] >= 2)
    is_early_shock = (stints['entry_over'] <= 4) & (stints['entry_wkts'] >= 1) & (stints['entry_runs'] <= 20)
    is_mid_collapse = (stints['entry_over'] <= 10) & (stints['entry_wkts'] >= 4)

    stints['is_collapse'] = (is_pp_collapse | is_early_shock | is_mid_collapse).astype(int)

    # Collapse severity score (0 to 10 scale)
    # Higher wickets lost in fewer overs = higher collapse crisis
    stints['crisis_severity'] = np.clip(
        (stints['entry_wkts'] * 12.0 - stints['entry_over'] * 4.0) / 10.0,
        0.0, 10.0
    )

    # Anchoring Performance on each collapse stint:
    # A successful rescue means surviving 20+ balls, scoring 25+ runs, and stabilizing/accelerating
    # Rescue Score = personal_runs * (balls_faced / 20.0) * crisis_severity
    stints['rescue_value'] = np.where(
        stints['is_collapse'] == 1,
        stints['personal_runs'] * np.minimum(1.5, stints['balls_faced'] / 20.0) * (1.0 + stints['crisis_severity'] / 5.0),
        0.0
    )

    # Aggregate Anchoring Metrics by Player
    anchoring_summary = stints.groupby(['player_id', 'player_name']).agg(
        total_stints=('match_id', 'count'),
        collapse_stints=('is_collapse', 'sum'),
        total_rescue_value=('rescue_value', 'sum'),
        collapse_runs=('personal_runs', lambda s: s[stints.loc[s.index, 'is_collapse'] == 1].sum()),
        collapse_balls=('balls_faced', lambda s: s[stints.loc[s.index, 'is_collapse'] == 1].sum()),
        avg_wp_tenure_shift=('wp_tenure_shift', 'mean')
    ).reset_index()

    anchoring_summary['collapse_sr'] = np.where(
        anchoring_summary['collapse_balls'] > 0,
        anchoring_summary['collapse_runs'] / anchoring_summary['collapse_balls'] * 100.0,
        0.0
    )

    # Anchoring Pressure Index (API):
    # Normalized score combining rescue value per collapse stint and strike rate under collapse
    anchoring_summary['anchoring_index'] = (
        anchoring_summary['total_rescue_value'] / (anchoring_summary['collapse_stints'] + 2.0)
    )

    print(f"  Anchoring metrics computed for {len(anchoring_summary)} batters.")
    return bbb, stints, anchoring_summary


def compute_phase_relative_metrics(bbb):
    """
    Compute Phase-Relative Value Added (PRVA) per player across Powerplay, Middle, Death.
    This equalizes top order (Powerplay swing/pace), middle order, and death-over finishers.
    """
    print("  Computing Phase-Relative Value Added (PRVA)...")

    legal = bbb[bbb['is_legal_delivery'] == 1].copy()

    # Per-batter phase stats
    player_phase = legal.groupby(['striker_id', 'phase']).agg(
        runs=('runs', 'sum'),
        balls=('runs', 'count'),
        xruns_sum=('xruns', 'sum'),
        xruns_delta_sum=('xruns_delta', 'sum')
    ).reset_index()

    # Pivot to get PP, Mid, Death metrics per player
    pivoted_delta = player_phase.pivot(index='striker_id', columns='phase', values='xruns_delta_sum').fillna(0)
    pivoted_balls = player_phase.pivot(index='striker_id', columns='phase', values='balls').fillna(0)

    prva_df = pd.DataFrame(index=pivoted_delta.index)
    prva_df['prva_powerplay'] = pivoted_delta.get('powerplay', 0)
    prva_df['prva_middle'] = pivoted_delta.get('middle', 0)
    prva_df['prva_death'] = pivoted_delta.get('death', 0)
    prva_df['prva_total'] = prva_df['prva_powerplay'] + prva_df['prva_middle'] + prva_df['prva_death']

    prva_df['balls_powerplay'] = pivoted_balls.get('powerplay', 0)
    prva_df['balls_middle'] = pivoted_balls.get('middle', 0)
    prva_df['balls_death'] = pivoted_balls.get('death', 0)
    prva_df['total_balls_all_phases'] = prva_df['balls_powerplay'] + prva_df['balls_middle'] + prva_df['balls_death']

    prva_df['prva_per_ball'] = prva_df['prva_total'] / np.maximum(prva_df['total_balls_all_phases'], 1)

    # Primary phase played by batter
    def get_primary_phase(row):
        bp, bm, bd = row['balls_powerplay'], row['balls_middle'], row['balls_death']
        if bp >= bm and bp >= bd:
            return 'Top Order (Powerplay)'
        elif bm >= bp and bm >= bd:
            return 'Middle Order'
        else:
            return 'Finisher (Death)'

    prva_df['role_phase'] = prva_df.apply(get_primary_phase, axis=1)
    prva_df = prva_df.reset_index().rename(columns={'index': 'striker_id'})

    print(f"  PRVA computed for {len(prva_df)} batters.")
    return prva_df
