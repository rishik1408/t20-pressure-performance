"""
Stage 4: Player Metrics & Composite Equalized Clutch Score
Computes enhanced batting and bowling pressure-performance metrics incorporating:
  1. Phase-Relative Benchmarking (Entry-Point Baselines, Collapse Rescue, Phase xRuns).
  2. Opposition Quality Weighting (Live Elo Multiplier & Bowler Matchup xV).
  3. Resistance to Drop-Off (High-Pressure vs Low-Pressure execution).
  4. Momentum Map & Bowling Pressure Index (BPI).
  5. Role-Segregated Classifications (Top Order, Middle Order, Death Specialists).
"""

import numpy as np
import pandas as pd
from scipy import stats


# ---------------------------------------------------------------------------
# Batting Metrics
# ---------------------------------------------------------------------------

def compute_batting_metrics(bbb, anchoring_summary=None, prva_df=None):
    """Compute all enhanced batting metrics per player."""
    print("  Computing enhanced batting metrics (with P-NPI and competition weighting)...")

    bat = bbb[bbb['is_legal_delivery'] == 1].copy()

    bat['is_dot'] = (bat['runs'] == 0).astype(int)
    bat['is_boundary'] = ((bat['is_four'] == True) | (bat['is_four'] == 'true') |
                          (bat['is_six'] == True) | (bat['is_six'] == 'true')).astype(int)

    # High pressure = PI >= 50, Low pressure = PI < 35
    bat['is_high_pressure'] = (bat['pressure_index'] >= 50.0).astype(int)
    bat['is_low_pressure'] = (bat['pressure_index'] < 35.0).astype(int)

    global_hp_sr = bat[bat['is_high_pressure'] == 1]['runs'].sum() / bat[bat['is_high_pressure'] == 1]['runs'].count() * 100.0

    grouped = bat.groupby(['striker_id', 'striker_name'])

    metrics = []
    for (player_id, player_name), group in grouped:
        n_balls = len(group)
        n_matches = group['match_id'].nunique()
        total_runs = group['runs'].sum()

        total_wpa = group['wpa_batting'].sum()
        wpa_per_ball = total_wpa / n_balls if n_balls > 0 else 0

        total_wpa_adj = group['wpa_batting_adj'].sum() if 'wpa_batting_adj' in group.columns else total_wpa
        wpa_adj_per_ball = total_wpa_adj / n_balls if n_balls > 0 else 0

        avg_comp_wt = group['comp_tier_multiplier'].mean() if 'comp_tier_multiplier' in group.columns else 1.0
        avg_matchup_mult = group['matchup_multiplier_bat'].mean() if 'matchup_multiplier_bat' in group.columns else 1.0

        # Contextual Batting Index (CBI)
        pi = group['pressure_index'].values
        runs_vals = group['runs'].values
        pi_sum = pi.sum()
        cbi = np.sum(runs_vals * pi) / pi_sum if pi_sum > 0 else 0

        if 'matchup_multiplier_bat' in group.columns:
            m_mult = group['matchup_multiplier_bat'].values
            weight = pi * m_mult
            w_sum = weight.sum()
            cbi_adj = np.sum(runs_vals * weight) / w_sum if w_sum > 0 else cbi
        else:
            cbi_adj = cbi

        overall_sr = (total_runs / n_balls * 100.0) if n_balls > 0 else 0

        # High-pressure metrics
        hp = group[group['is_high_pressure'] == 1]
        hp_balls = len(hp)
        hp_runs = hp['runs'].sum()
        hp_sr = (hp_runs / hp_balls * 100.0) if hp_balls > 0 else np.nan
        hp_dots = hp['is_dot'].sum()
        hp_dot_pct = (hp_dots / hp_balls * 100.0) if hp_balls > 0 else np.nan
        hp_boundaries = hp['is_boundary'].sum()
        hp_boundary_pct = (hp_boundaries / hp_balls * 100.0) if hp_balls > 0 else np.nan

        # Low-pressure metrics
        lp = group[group['is_low_pressure'] == 1]
        lp_balls = len(lp)
        lp_runs = lp['runs'].sum()
        lp_sr = (lp_runs / lp_balls * 100.0) if lp_balls > 0 else np.nan

        # Drop-off ratio (HP SR / LP SR)
        drop_off = hp_sr / lp_sr if (lp_sr and lp_sr > 0 and hp_sr is not np.nan and not np.isnan(hp_sr)) else np.nan

        # Cumulative runs above replacement in high-pressure situations
        hp_runs_above_base = (hp_sr - 125.0) * (hp_balls / 100.0) * avg_comp_wt if pd.notna(hp_sr) else 0.0

        # Primary batting phase & batting order
        pp_balls = len(group[group['overid'] <= 6])
        mid_balls = len(group[(group['overid'] >= 7) & (group['overid'] <= 15)])
        death_balls = len(group[group['overid'] >= 16])

        avg_order = group['batting_order'].dropna().astype(float).mean() if 'batting_order' in group.columns else 4.0

        if pp_balls >= mid_balls and pp_balls >= death_balls:
            primary_role = 'Top-Order Anchor / PP'
        elif mid_balls >= pp_balls and mid_balls >= death_balls:
            primary_role = 'Middle-Order Engine'
        else:
            primary_role = 'Death Finisher'

        metrics.append({
            'player_id': player_id,
            'player_name': player_name,
            'matches': n_matches,
            'balls_faced': n_balls,
            'total_runs': total_runs,
            'overall_sr': overall_sr,
            'total_wpa': total_wpa,
            'wpa_per_ball': wpa_per_ball,
            'total_wpa_adj': total_wpa_adj,
            'wpa_adj_per_ball': wpa_adj_per_ball,
            'avg_comp_wt': avg_comp_wt,
            'avg_matchup_mult': avg_matchup_mult,
            'cbi': cbi,
            'cbi_adj': cbi_adj,
            'hp_balls': hp_balls,
            'hp_runs': hp_runs,
            'hp_sr': hp_sr,
            'lp_balls': lp_balls,
            'lp_runs': lp_runs,
            'lp_sr': lp_sr,
            'drop_off_ratio': drop_off,
            'hp_dot_pct': hp_dot_pct,
            'hp_boundary_pct': hp_boundary_pct,
            'hp_runs_above_base': hp_runs_above_base,
            'pp_balls': pp_balls,
            'mid_balls': mid_balls,
            'death_balls': death_balls,
            'avg_batting_order': avg_order,
            'primary_role': primary_role
        })

    df = pd.DataFrame(metrics)

    # Merge Anchoring Metrics
    if anchoring_summary is not None:
        df = df.merge(
            anchoring_summary[['player_id', 'collapse_stints', 'collapse_runs', 'collapse_sr', 'anchoring_index']],
            on='player_id',
            how='left'
        )
        df['collapse_stints'] = df['collapse_stints'].fillna(0)
        df['collapse_runs'] = df['collapse_runs'].fillna(0)
        df['collapse_sr'] = df['collapse_sr'].fillna(0)
        df['anchoring_index'] = df['anchoring_index'].fillna(0)
    else:
        df['anchoring_index'] = 0.0
        df['collapse_runs'] = 0.0

    # Merge PRVA
    if prva_df is not None:
        df = df.merge(
            prva_df[['striker_id', 'prva_total', 'prva_per_ball']].rename(columns={'striker_id': 'player_id'}),
            on='player_id',
            how='left'
        )
        df['prva_total'] = df['prva_total'].fillna(0)
        df['prva_per_ball'] = df['prva_per_ball'].fillna(0)
    else:
        df['prva_total'] = 0.0
        df['prva_per_ball'] = 0.0

    print(f"  Computed enhanced batting metrics for {len(df)} players")
    return df


# ---------------------------------------------------------------------------
# Bowling Metrics
# ---------------------------------------------------------------------------

def compute_momentum_red_zones(bbb):
    """
    Identify 'red zone' deliveries where the batting team scored 10+ runs
    in any of the preceding 3 completed overs.
    """
    over_runs = bbb.groupby(['match_id', 'innings', 'overid'])['total_off_ball'].sum().reset_index()
    over_runs.columns = ['match_id', 'innings', 'overid', 'over_total_runs']

    red_zone_overs = set()
    for (mid, inn), grp in over_runs.groupby(['match_id', 'innings']):
        grp = grp.sort_values('overid')
        overs_list = grp[['overid', 'over_total_runs']].values.tolist()
        for i, (ov, _) in enumerate(overs_list):
            prev_overs = [overs_list[j] for j in range(max(0, i-3), i)]
            if any(r >= 10 for _, r in prev_overs):
                red_zone_overs.add((mid, inn, int(ov)))

    bbb_keys = list(zip(bbb['match_id'], bbb['innings'], bbb['overid']))
    is_red_zone = np.array([k in red_zone_overs for k in bbb_keys])
    return is_red_zone


def compute_bowling_metrics(bbb):
    """Compute all enhanced bowling metrics per player."""
    print("  Computing enhanced bowling metrics (with P-NPI and competition weighting)...")

    is_red_zone = compute_momentum_red_zones(bbb)
    bbb = bbb.copy()
    bbb['is_red_zone'] = is_red_zone

    bowl = bbb.copy()

    bowl['is_high_pressure'] = (bowl['pressure_index'] >= 50.0).astype(int)
    bowl['is_low_pressure'] = (bowl['pressure_index'] < 35.0).astype(int)

    bowler_dismissals = {'Bowled', 'Caught', 'LBW', 'Stump', 'Hit Wicket'}
    bowl['is_bowler_wicket'] = (
        (bowl['is_wicket_int'] == 1) &
        bowl['dismissal_type'].isin(bowler_dismissals)
    ).astype(int)

    # Global high-pressure economy
    hp_balls_global = bowl[bowl['is_high_pressure'] == 1]
    global_hp_econ = hp_balls_global['total_off_ball'].sum() / (len(hp_balls_global) / 6.0)

    # Red zone economy
    red_zone_balls = bowl[bowl['is_red_zone'] == True]
    global_rz_economy = (red_zone_balls['total_off_ball'].sum() / (len(red_zone_balls) / 6.0)) if len(red_zone_balls) > 0 else 8.0

    global_mean_rpb = bowl['total_off_ball'].mean()

    grouped = bowl.groupby(['bowler_id', 'bowler_name'])

    metrics = []
    for (player_id, player_name), group in grouped:
        n_balls = len(group)
        n_matches = group['match_id'].nunique()
        total_runs_conceded = group['total_off_ball'].sum()
        total_wickets = group['is_bowler_wicket'].sum()

        overs_bowled = n_balls / 6.0
        economy = total_runs_conceded / overs_bowled if overs_bowled > 0 else np.nan

        total_wpa = group['wpa_bowling'].sum()
        wpa_per_ball = total_wpa / n_balls if n_balls > 0 else 0

        total_wpa_adj = group['wpa_bowling_adj'].sum() if 'wpa_bowling_adj' in group.columns else total_wpa
        wpa_adj_per_ball = total_wpa_adj / n_balls if n_balls > 0 else 0

        avg_comp_wt = group['comp_tier_multiplier'].mean() if 'comp_tier_multiplier' in group.columns else 1.0
        avg_matchup_mult = group['matchup_multiplier_bowl'].mean() if 'matchup_multiplier_bowl' in group.columns else 1.0

        # Contextual Bowling Index
        pi = group['pressure_index'].values
        actual_runs = group['total_off_ball'].values
        pi_sum = pi.sum()
        runs_saved = global_mean_rpb - actual_runs
        cboi = np.sum(runs_saved * pi) / pi_sum if pi_sum > 0 else 0

        if 'bowling_xruns_saved' in group.columns and 'matchup_multiplier_bowl' in group.columns:
            m_mult = group['matchup_multiplier_bowl'].values
            phase_saved = group['bowling_xruns_saved'].values
            w = pi * m_mult
            w_sum = w.sum()
            cboi_adj = np.sum(phase_saved * w) / w_sum if w_sum > 0 else cboi
        else:
            cboi_adj = cboi

        # High-pressure metrics
        hp = group[group['is_high_pressure'] == 1]
        hp_balls = len(hp)
        hp_runs = hp['total_off_ball'].sum()
        hp_overs = hp_balls / 6.0
        hp_econ = hp_runs / hp_overs if hp_overs > 0 else np.nan
        hp_wickets = hp['is_bowler_wicket'].sum()
        hp_wkts_per_ball = hp_wickets / hp_balls if hp_balls > 0 else np.nan

        # Batter quality weighted wickets
        if hp_balls > 0 and 'batter_matchup_multiplier' in hp.columns:
            hp_wkt_quality = (hp['is_bowler_wicket'] * hp['batter_matchup_multiplier']).sum() / hp_balls
        else:
            hp_wkt_quality = hp_wkts_per_ball

        # Runs saved under pressure
        hp_runs_saved = (global_hp_econ - hp_econ) * (hp_balls / 6.0) * avg_comp_wt if pd.notna(hp_econ) else 0.0

        # Low-pressure metrics
        lp = group[group['is_low_pressure'] == 1]
        lp_balls = len(lp)
        lp_runs = lp['total_off_ball'].sum()
        lp_overs = lp_balls / 6.0
        lp_econ = lp_runs / lp_overs if lp_overs > 0 else np.nan

        bowling_drop_off = lp_econ / hp_econ if (hp_econ and hp_econ > 0 and not np.isnan(hp_econ)) else np.nan

        # BPI: Momentum Map performance
        rz = group[group['is_red_zone'] == True]
        rz_balls = len(rz)
        if rz_balls >= 6:
            rz_runs = rz['total_off_ball'].sum()
            rz_econ = rz_runs / (rz_balls / 6.0)
            bpi = (global_rz_economy - rz_econ) / global_rz_economy if global_rz_economy > 0 else 0
        else:
            bpi = np.nan

        # Primary bowling phase
        pp_balls = len(group[group['overid'] <= 6])
        mid_balls = len(group[(group['overid'] >= 7) & (group['overid'] <= 15)])
        death_balls = len(group[group['overid'] >= 16])

        if pp_balls >= mid_balls and pp_balls >= death_balls:
            primary_role = 'Powerplay Strike Bowler'
        elif mid_balls >= pp_balls and mid_balls >= death_balls:
            primary_role = 'Middle-Overs Choke / Spin'
        else:
            primary_role = 'Death Overs Specialist'

        metrics.append({
            'player_id': player_id,
            'player_name': player_name,
            'matches': n_matches,
            'balls_bowled': n_balls,
            'total_runs_conceded': total_runs_conceded,
            'total_wickets': total_wickets,
            'economy': economy,
            'total_wpa': total_wpa,
            'wpa_per_ball': wpa_per_ball,
            'total_wpa_adj': total_wpa_adj,
            'wpa_adj_per_ball': wpa_adj_per_ball,
            'avg_comp_wt': avg_comp_wt,
            'avg_matchup_mult': avg_matchup_mult,
            'cboi': cboi,
            'cboi_adj': cboi_adj,
            'hp_balls': hp_balls,
            'hp_runs': hp_runs,
            'hp_econ': hp_econ,
            'hp_wickets': hp_wickets,
            'hp_runs_saved': hp_runs_saved,
            'lp_balls': lp_balls,
            'lp_runs': lp_runs,
            'lp_econ': lp_econ,
            'bowling_drop_off': bowling_drop_off,
            'hp_wkts_per_ball': hp_wkts_per_ball,
            'hp_wkt_quality': hp_wkt_quality,
            'bpi': bpi,
            'rz_balls': rz_balls,
            'pp_balls': pp_balls,
            'mid_balls': mid_balls,
            'death_balls': death_balls,
            'primary_role': primary_role
        })

    df = pd.DataFrame(metrics)
    print(f"  Computed enhanced bowling metrics for {len(df)} players")
    return df


# ---------------------------------------------------------------------------
# Composite Scoring & Ranking
# ---------------------------------------------------------------------------

def zscore_series(s):
    """Compute z-scores for a series, handling NaN."""
    mean = s.mean()
    std = s.std()
    if std == 0 or np.isnan(std):
        return pd.Series(0, index=s.index)
    return (s - mean) / std


def compute_batting_clutch_score(bat_metrics):
    """
    Compute balanced composite batting clutch score:
      - High-Pressure Runs Above Replacement (Volume + Rate): 30%
      - Matchup-Adjusted WPA per ball: 25%
      - Resistance to Drop-Off: 20%
      - Anchoring Pressure Index (API): 15%
      - Phase-Relative Value Added (PRVA xRuns): 10%
    """
    print("  Computing balanced batting composite clutch scores...")

    df = bat_metrics.copy()

    # Robust eligibility: 400+ balls faced, 50+ high-pressure balls, 15+ matches
    eligible = (df['balls_faced'] >= 400) & (df['hp_balls'] >= 50) & (df['matches'] >= 15)
    df_elig = df[eligible].copy()
    print(f"  Eligible batters (min 400 balls, 50 HP balls): {len(df_elig)} (from {len(df)} total)")

    if len(df_elig) < 20:
        eligible = (df['balls_faced'] >= 300) & (df['hp_balls'] >= 30) & (df['matches'] >= 10)
        df_elig = df[eligible].copy()
        print(f"  Eligible batters (relaxed): {len(df_elig)}")

    # Bayesian shrinkage on Drop-Off ratio (weight = 30 balls)
    pop_median_dropoff = df_elig['drop_off_ratio'].median()
    df_elig['shrunk_dropoff'] = (df_elig['hp_balls'] * df_elig['drop_off_ratio'].fillna(pop_median_dropoff) + 30.0 * pop_median_dropoff) / (df_elig['hp_balls'] + 30.0)

    # Z-scores
    z_vol_rate = zscore_series(df_elig['hp_runs_above_base'])
    z_wpa_adj = zscore_series(df_elig['wpa_adj_per_ball'])
    z_dropoff = zscore_series(df_elig['shrunk_dropoff'])
    z_anchoring = zscore_series(df_elig['anchoring_index'].fillna(0))
    z_prva = zscore_series(df_elig['prva_per_ball'].fillna(0))

    composite = (0.30 * z_vol_rate +
                 0.25 * z_wpa_adj +
                 0.20 * z_dropoff +
                 0.15 * z_anchoring +
                 0.10 * z_prva)

    c_min, c_max = composite.min(), composite.max()
    normalized = 100.0 * (composite - c_min) / (c_max - c_min) if c_max > c_min else pd.Series(50.0, index=composite.index)

    df_elig['z_vol_rate'] = z_vol_rate
    df_elig['z_wpa_adj'] = z_wpa_adj
    df_elig['z_dropoff'] = z_dropoff
    df_elig['z_anchoring'] = z_anchoring
    df_elig['z_prva'] = z_prva
    df_elig['composite_raw'] = composite
    df_elig['clutch_score'] = normalized

    df_elig = df_elig.sort_values('clutch_score', ascending=False).reset_index(drop=True)
    df_elig['rank'] = range(1, len(df_elig) + 1)

    return df_elig


def compute_bowling_clutch_score(bowl_metrics):
    """
    Compute balanced composite bowling clutch score:
      - High-Pressure Runs Saved (Volume + Rate): 30%
      - Matchup-Adjusted Bowling WPA per ball: 25%
      - Bowling Resistance to Drop-Off: 20%
      - Momentum Map BPI: 15%
      - High-Pressure Wicket Quality: 10%
    """
    print("  Computing balanced bowling composite clutch scores...")

    df = bowl_metrics.copy()

    # Robust eligibility: 400+ balls bowled, 50+ high-pressure balls, 15+ matches
    eligible = (df['balls_bowled'] >= 400) & (df['hp_balls'] >= 50) & (df['matches'] >= 15)
    df_elig = df[eligible].copy()
    print(f"  Eligible bowlers (min 400 balls, 50 HP balls): {len(df_elig)} (from {len(df)} total)")

    if len(df_elig) < 20:
        eligible = (df['balls_bowled'] >= 300) & (df['hp_balls'] >= 30) & (df['matches'] >= 10)
        df_elig = df[eligible].copy()
        print(f"  Eligible bowlers (relaxed): {len(df_elig)}")

    # Bayesian shrinkage on Drop-Off ratio
    pop_median_dropoff = df_elig['bowling_drop_off'].median()
    df_elig['shrunk_dropoff'] = (df_elig['hp_balls'] * df_elig['bowling_drop_off'].fillna(pop_median_dropoff) + 30.0 * pop_median_dropoff) / (df_elig['hp_balls'] + 30.0)

    # Z-scores
    z_runs_saved = zscore_series(df_elig['hp_runs_saved'])
    z_wpa_adj = zscore_series(df_elig['wpa_adj_per_ball'])
    z_dropoff = zscore_series(df_elig['shrunk_dropoff'])
    z_bpi = zscore_series(df_elig['bpi'].fillna(df_elig['bpi'].median()))
    z_wkts_adj = zscore_series(df_elig['hp_wkt_quality'].fillna(0))

    composite = (0.30 * z_runs_saved +
                 0.25 * z_wpa_adj +
                 0.20 * z_dropoff +
                 0.15 * z_bpi +
                 0.10 * z_wkts_adj)

    c_min, c_max = composite.min(), composite.max()
    normalized = 100.0 * (composite - c_min) / (c_max - c_min) if c_max > c_min else pd.Series(50.0, index=composite.index)

    df_elig['z_runs_saved'] = z_runs_saved
    df_elig['z_wpa_adj'] = z_wpa_adj
    df_elig['z_dropoff'] = z_dropoff
    df_elig['z_bpi'] = z_bpi
    df_elig['z_wkts_adj'] = z_wkts_adj
    df_elig['composite_raw'] = composite
    df_elig['clutch_score'] = normalized

    df_elig = df_elig.sort_values('clutch_score', ascending=False).reset_index(drop=True)
    df_elig['rank'] = range(1, len(df_elig) + 1)

    return df_elig


def get_role_segregated_rankings(bat_ranked, bowl_ranked):
    """
    Extract dedicated role-segregated top leaderboards:
    Batters:
      - Top-Order Anchors & PP Enforcers (Top 5)
      - Middle-Order Engines & Rebuilders (Top 5)
      - Death-Over Finishers (Top 5)
    Bowlers:
      - Powerplay Strike Bowlers (Top 5)
      - Middle-Overs Spin & Choke (Top 5)
      - Death-Overs Specialists (Top 5)
    """
    # Batting Roles
    bat_top_order = bat_ranked[bat_ranked['primary_role'] == 'Top-Order Anchor / PP'].copy().reset_index(drop=True)
    bat_top_order['role_rank'] = range(1, len(bat_top_order) + 1)

    bat_middle = bat_ranked[bat_ranked['primary_role'] == 'Middle-Order Engine'].copy().reset_index(drop=True)
    bat_middle['role_rank'] = range(1, len(bat_middle) + 1)

    bat_death = bat_ranked[bat_ranked['primary_role'] == 'Death Finisher'].copy().reset_index(drop=True)
    bat_death['role_rank'] = range(1, len(bat_death) + 1)

    # Bowling Roles
    bowl_pp = bowl_ranked[bowl_ranked['primary_role'] == 'Powerplay Strike Bowler'].copy().reset_index(drop=True)
    bowl_pp['role_rank'] = range(1, len(bowl_pp) + 1)

    bowl_mid = bowl_ranked[bowl_ranked['primary_role'] == 'Middle-Overs Choke / Spin'].copy().reset_index(drop=True)
    bowl_mid['role_rank'] = range(1, len(bowl_mid) + 1)

    bowl_death = bowl_ranked[bowl_ranked['primary_role'] == 'Death Overs Specialist'].copy().reset_index(drop=True)
    bowl_death['role_rank'] = range(1, len(bowl_death) + 1)

    return {
        'bat_top_order': bat_top_order.head(5),
        'bat_middle': bat_middle.head(5),
        'bat_death': bat_death.head(5),
        'bowl_pp': bowl_pp.head(5),
        'bowl_mid': bowl_mid.head(5),
        'bowl_death': bowl_death.head(5),
    }


def run_player_metrics(bbb, anchoring_summary=None, prva_df=None):
    """Main entry point for Stage 4."""
    print("Stage 4: Computing Player Metrics & Clutch Scores...")
    bat_metrics = compute_batting_metrics(bbb, anchoring_summary=anchoring_summary, prva_df=prva_df)
    bowl_metrics = compute_bowling_metrics(bbb)
    bat_ranked = compute_batting_clutch_score(bat_metrics)
    bowl_ranked = compute_bowling_clutch_score(bowl_metrics)
    role_rankings = get_role_segregated_rankings(bat_ranked, bowl_ranked)
    return bat_metrics, bowl_metrics, bat_ranked, bowl_ranked, role_rankings
