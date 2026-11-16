"""
Opposition Quality & Competition Tier Weighting
Computes:
  1. Competition Tier Index (IPL / ICC: 1.30x, Tier-1 Bilaterals: 1.10x, Associate/Emerging: 0.75x).
  2. Live Elo ratings for all teams chronologically across matches.
  3. Phase-specific empirical Bayes bowler ratings (Matchup xV).
  4. Phase-specific empirical Bayes batter ratings (Batter Threat Multiplier).
  5. Delivery-level composite matchup multipliers applied to WPA and Contextual Indices.
"""

import numpy as np
import pandas as pd


def get_competition_tier_multiplier(comp_name):
    """
    Tier 1 (1.30x): IPL (2022-2026), ICC World Cup tournaments.
    Tier 2 (1.10x): Full-member international bilaterals (IND, AUS, ENG, SA, NZ, PAK, WI).
    Tier 3 (0.75x): Emerging Teams Asia Cup, Rising Stars, Associate Tri-series.
    """
    c = str(comp_name).lower()
    if 'ipl' in c or 'world cup' in c:
        return 1.30

    tier1_nations = {'india', 'australia', 'england', 'south africa', 'new zealand', 'pakistan', 'west indies'}
    if any(n in c for n in tier1_nations):
        if 'emerging' in c or 'rising' in c or ' a ' in c or 'a team' in c:
            return 0.75
        return 1.10

    return 0.75


def compute_team_elos(matches):
    """
    Compute live chronological Elo ratings for all teams.
    Returns a dictionary of (match_id, team_id) -> pre-match Elo,
    and a dictionary of final team Elos.
    """
    print("  Computing chronological team Elo ratings...")

    completed = matches[matches['win_team_id'].notna() & (matches['win_team_id'] != '')].copy()
    completed['win_team_id'] = completed['win_team_id'].astype(int)
    completed = completed.sort_values('match_date').reset_index(drop=True)

    elo = {}
    pre_match_elos = {}
    K = 32.0
    BASE_ELO = 1500.0

    for _, row in completed.iterrows():
        mid = row['match_id']
        h = int(row['home_team_id'])
        a = int(row['away_team_id'])
        w = int(row['win_team_id'])

        r_h = elo.get(h, BASE_ELO)
        r_a = elo.get(a, BASE_ELO)

        pre_match_elos[(mid, h)] = r_h
        pre_match_elos[(mid, a)] = r_a

        e_h = 1.0 / (1.0 + 10.0 ** ((r_a - r_h) / 400.0))
        e_a = 1.0 - e_h

        s_h = 1.0 if w == h else (0.5 if w == 0 else 0.0)
        s_a = 1.0 - s_h

        elo[h] = r_h + K * (s_h - e_h)
        elo[a] = r_a + K * (s_a - e_a)

    print(f"  Computed Elo ratings across {len(completed)} matches for {len(elo)} teams.")
    return pre_match_elos, elo


def compute_bowler_phase_ratings(bbb):
    """
    Compute empirical Bayes phase-specific economy rates for all bowlers.
    Phases: powerplay (overs 1-6), middle (overs 7-15), death (overs 16-20).
    """
    print("  Computing bowler phase-specific ratings (Matchup xV)...")

    phase_econ = bbb.groupby('phase').agg(
        total_runs=('total_off_ball', 'sum'),
        total_balls=('total_off_ball', 'count')
    ).reset_index()
    phase_econ['global_econ'] = phase_econ['total_runs'] / (phase_econ['total_balls'] / 6.0)
    global_phase_map = dict(zip(phase_econ['phase'], phase_econ['global_econ']))

    bowler_phase = bbb.groupby(['bowler_id', 'phase']).agg(
        runs=('total_off_ball', 'sum'),
        balls=('total_off_ball', 'count')
    ).reset_index()

    prior_weight = 30.0
    multipliers = {}

    for _, row in bowler_phase.iterrows():
        bid = row['bowler_id']
        phase = row['phase']
        g_econ = global_phase_map.get(phase, 8.5)

        shrunk_econ = (row['runs'] + prior_weight * (g_econ / 6.0)) / ((row['balls'] + prior_weight) / 6.0)
        mult = np.clip(g_econ / max(shrunk_econ, 4.0), 0.65, 1.50)
        multipliers[(bid, phase)] = mult

    return multipliers, global_phase_map


def compute_batter_phase_ratings(bbb):
    """
    Compute empirical Bayes phase-specific strike rates for all batters.
    """
    print("  Computing batter phase-specific ratings (Batter Threat Multiplier)...")

    legal = bbb[bbb['is_legal_delivery'] == 1].copy()

    phase_sr = legal.groupby('phase').agg(
        total_runs=('runs', 'sum'),
        total_balls=('runs', 'count')
    ).reset_index()
    phase_sr['global_sr'] = (phase_sr['total_runs'] / phase_sr['total_balls']) * 100.0
    global_sr_map = dict(zip(phase_sr['phase'], phase_sr['global_sr']))

    batter_phase = legal.groupby(['striker_id', 'phase']).agg(
        runs=('runs', 'sum'),
        balls=('runs', 'count')
    ).reset_index()

    prior_weight = 30.0
    multipliers = {}

    for _, row in batter_phase.iterrows():
        sid = row['striker_id']
        phase = row['phase']
        g_sr = global_sr_map.get(phase, 130.0)

        shrunk_sr = (row['runs'] + prior_weight * (g_sr / 100.0)) / (row['balls'] + prior_weight) * 100.0
        mult = np.clip(shrunk_sr / g_sr, 0.65, 1.50)
        multipliers[(sid, phase)] = mult

    return multipliers, global_sr_map


def enrich_matchup_multipliers(bbb, matches):
    """
    Enrich every delivery in bbb with Competition Tier multipliers,
    Team Elo multipliers, and Bowler/Batter Matchup xV.
    """
    print("Stage: Enriching opposition quality and matchup multipliers...")

    bbb['phase'] = np.where(bbb['overid'] <= 6, 'powerplay',
                   np.where(bbb['overid'] <= 15, 'middle', 'death'))

    # Merge comp_name from matches if not present
    if 'comp_name' not in bbb.columns:
        bbb = bbb.merge(matches[['match_id', 'comp_name']], on='match_id', how='left')

    # 1. Competition Tier Multiplier
    bbb['comp_tier_multiplier'] = bbb['comp_name'].apply(get_competition_tier_multiplier)

    # 2. Team Elo Multipliers
    pre_match_elos, final_elos = compute_team_elos(matches)

    bowling_team_elos = [pre_match_elos.get((mid, btid), 1500.0)
                         for mid, btid in zip(bbb['match_id'], bbb['bowling_team_id'])]
    batting_team_elos = [pre_match_elos.get((mid, btid), 1500.0)
                         for mid, btid in zip(bbb['match_id'], bbb['batting_team_id'])]

    bbb['bowling_team_elo'] = bowling_team_elos
    bbb['batting_team_elo'] = batting_team_elos

    bbb['team_elo_multiplier_bat'] = np.clip((bbb['bowling_team_elo'] / 1500.0) ** 1.2, 0.80, 1.25)
    bbb['team_elo_multiplier_bowl'] = np.clip((bbb['batting_team_elo'] / 1500.0) ** 1.2, 0.80, 1.25)

    # 3. Bowler & Batter Matchup Ratings
    bowler_mults, global_phase_econ = compute_bowler_phase_ratings(bbb)
    batter_mults, global_phase_sr = compute_batter_phase_ratings(bbb)

    bbb['bowler_matchup_multiplier'] = [bowler_mults.get((bid, p), 1.0)
                                        for bid, p in zip(bbb['bowler_id'], bbb['phase'])]
    bbb['batter_matchup_multiplier'] = [batter_mults.get((sid, p), 1.0)
                                        for sid, p in zip(bbb['striker_id'], bbb['phase'])]

    # 4. Total Composite Matchup Multipliers
    bbb['matchup_multiplier_bat'] = (bbb['team_elo_multiplier_bat'] *
                                     bbb['bowler_matchup_multiplier'] *
                                     bbb['comp_tier_multiplier'])

    bbb['matchup_multiplier_bowl'] = (bbb['team_elo_multiplier_bowl'] *
                                      bbb['batter_matchup_multiplier'] *
                                      bbb['comp_tier_multiplier'])

    # 5. Adjusted WPA
    bbb['wpa_batting_adj'] = bbb['wpa_batting'] * bbb['matchup_multiplier_bat']
    bbb['wpa_bowling_adj'] = bbb['wpa_bowling'] * bbb['matchup_multiplier_bowl']

    print(f"  Matchup multipliers enriched: mean_bat={bbb['matchup_multiplier_bat'].mean():.3f}, "
          f"mean_bowl={bbb['matchup_multiplier_bowl'].mean():.3f}")

    return bbb, final_elos
