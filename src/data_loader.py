"""
Stage 1: Data Loading & Cleaning
Loads all CSVs, joins them, and builds the enriched ball-by-ball table
with running match state for every delivery.
"""

import pandas as pd
import numpy as np
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_raw_data():
    """Load all raw CSV files."""
    bbb = pd.read_csv(os.path.join(DATA_DIR, 'ball_by_ball.csv'))
    matches = pd.read_csv(os.path.join(DATA_DIR, 'matches.csv'))
    competitions = pd.read_csv(os.path.join(DATA_DIR, 'competitions.csv'))
    playing_xi = pd.read_csv(os.path.join(DATA_DIR, 'playing_eleven.csv'))
    mapping = pd.read_csv(os.path.join(DATA_DIR, 'competition_team_player_mapping.csv'))
    teams = pd.read_csv(os.path.join(DATA_DIR, 'teams.csv'))
    return bbb, matches, competitions, playing_xi, mapping, teams


def enrich_matches(matches, competitions):
    """Join matches with competitions to get format, season, stage info."""
    matches = matches.merge(
        competitions[['comp_id', 'comp_name', 'match_format', 'season']],
        on='comp_id', how='left'
    )
    # Assign competition weights based on tournament tier
    def get_comp_weight(comp_name):
        c = str(comp_name).lower()
        if 'ipl' in c or 'world cup' in c:
            return 1.3
        tier1 = {'india', 'australia', 'england', 'south africa', 'new zealand', 'pakistan', 'west indies'}
        if any(t in c for t in tier1):
            if 'emerging' in c or 'rising' in c or 'a team' in c:
                return 0.75
            return 1.1
        return 0.75

    matches['comp_weight'] = matches['comp_name'].apply(get_comp_weight)
    return matches


def compute_innings_target(bbb, matches):
    """Compute the target for 2nd innings (1st innings total + 1, or DLS revised target)."""
    # Compute first innings totals per match
    first_inn = bbb[bbb['innings'] == 1].copy()
    first_inn['total_off_ball'] = first_inn['runs'] + first_inn['extras1_runs'] + first_inn['extras_2_runs']
    first_inn_totals = first_inn.groupby('match_id')['total_off_ball'].sum().reset_index()
    first_inn_totals.columns = ['match_id', 'first_innings_total']

    # Merge with matches to get revised_target
    targets = matches[['match_id', 'revised_target']].merge(first_inn_totals, on='match_id', how='left')
    targets['target'] = targets.apply(
        lambda row: int(row['revised_target']) if pd.notna(row['revised_target']) and int(row['revised_target']) > 0
        else (row['first_innings_total'] + 1 if pd.notna(row['first_innings_total']) else np.nan),
        axis=1
    )
    return targets[['match_id', 'target', 'first_innings_total']]


def build_enriched_bbb(bbb, matches, competitions):
    """
    Build the enriched ball-by-ball DataFrame with running match state.
    Returns the enriched DataFrame and enriched matches DataFrame.
    """
    print("  Loading and enriching matches...")
    matches_enriched = enrich_matches(matches, competitions)
    valid_match_ids = set(matches_enriched['match_id'].values)

    # Filter ball-by-ball to regular innings (1, 2 only)
    print("  Filtering to regular innings (1, 2 only)...")
    bbb = bbb[bbb['innings'].isin([1, 2])].copy()

    # Compute total runs off each ball
    bbb['total_off_ball'] = bbb['runs'] + bbb['extras1_runs'] + bbb['extras_2_runs']

    # Mark legal deliveries (not wides — wides don't count as balls faced)
    bbb['is_legal_delivery'] = (~bbb['extras_type'].isin(['wide'])).astype(int)

    # Also mark balls that count for the bowler (wides DO count for the over but don't count as legal delivery for batter)
    # Actually in cricket, wides don't count toward the over either. Let's be precise:
    # Legal delivery = not wide and not no-ball-that's-also-wide
    # For overs: wides and no-balls don't count
    bbb['is_ball_for_over'] = (~bbb['extras_type'].isin(['wide', 'Overstep'])).astype(int)

    # Sort by match, innings, over, ball number
    bbb = bbb.sort_values(['match_id', 'innings', 'overid', 'over_ball_num', 'innings_ball_num']).reset_index(drop=True)

    # --- Compute running state per innings ---
    print("  Computing running match state per innings...")

    # Group by match_id, innings for cumulative calculations
    group_cols = ['match_id', 'innings']

    # Cumulative runs (including current ball)
    bbb['total_runs_so_far'] = bbb.groupby(group_cols)['total_off_ball'].cumsum()

    # Cumulative runs BEFORE this ball (for WP "before" state)
    bbb['total_runs_before'] = bbb['total_runs_so_far'] - bbb['total_off_ball']

    # Cumulative legal deliveries (for overs calculation)
    bbb['legal_balls_so_far'] = bbb.groupby(group_cols)['is_ball_for_over'].cumsum()
    bbb['legal_balls_before'] = bbb['legal_balls_so_far'] - bbb['is_ball_for_over']

    # Cumulative wickets
    bbb['is_wicket_int'] = bbb['is_wicket'].apply(lambda x: 1 if x == True or x == 'true' or x == 'True' else 0)
    bbb['wickets_so_far'] = bbb.groupby(group_cols)['is_wicket_int'].cumsum()
    bbb['wickets_before'] = bbb['wickets_so_far'] - bbb['is_wicket_int']

    # Overs bowled (legal balls / 6)
    bbb['overs_bowled_before'] = bbb['legal_balls_before'] / 6.0
    bbb['overs_bowled_after'] = bbb['legal_balls_so_far'] / 6.0

    # DLS revised overs handling
    bbb_with_match = bbb.merge(
        matches_enriched[['match_id', 'first_inn_revised_overs', 'second_inn_revised_overs']],
        on='match_id', how='left'
    )

    # Total overs in innings
    def get_total_overs(row):
        if row['innings'] == 1:
            rev = row.get('first_inn_revised_overs', 0)
            if pd.notna(rev) and rev > 0:
                return float(rev)
            return 20.0
        else:
            rev = row.get('second_inn_revised_overs', 0)
            if pd.notna(rev) and rev > 0:
                return float(rev)
            return 20.0

    bbb['total_overs_in_innings'] = bbb_with_match.apply(get_total_overs, axis=1)
    total_balls_in_innings = bbb['total_overs_in_innings'] * 6

    # Balls remaining
    bbb['balls_remaining_before'] = (total_balls_in_innings - bbb['legal_balls_before']).clip(lower=0)
    bbb['balls_remaining_after'] = (total_balls_in_innings - bbb['legal_balls_so_far']).clip(lower=0)

    # Wickets in hand
    bbb['wickets_in_hand_before'] = 10 - bbb['wickets_before']
    bbb['wickets_in_hand_after'] = 10 - bbb['wickets_so_far']

    # Current run rate
    bbb['crr_before'] = np.where(
        bbb['overs_bowled_before'] > 0,
        bbb['total_runs_before'] / bbb['overs_bowled_before'],
        0.0
    )

    # --- Compute 2nd innings specific fields ---
    print("  Computing 2nd innings chase fields...")
    targets = compute_innings_target(bbb, matches_enriched)
    bbb = bbb.merge(targets, on='match_id', how='left')

    # Runs required (2nd innings only)
    bbb['runs_required_before'] = np.where(
        bbb['innings'] == 2,
        bbb['target'] - bbb['total_runs_before'],
        np.nan
    )
    bbb['runs_required_after'] = np.where(
        bbb['innings'] == 2,
        bbb['target'] - bbb['total_runs_so_far'],
        np.nan
    )

    # Required run rate (2nd innings only)
    overs_remaining_before = bbb['balls_remaining_before'] / 6.0
    bbb['rrr_before'] = np.where(
        (bbb['innings'] == 2) & (overs_remaining_before > 0),
        bbb['runs_required_before'] / overs_remaining_before,
        np.nan
    )

    # --- Batter experience on crease ---
    print("  Computing batter crease experience...")
    # Count legal deliveries faced by each striker within each innings
    bbb['striker_ball_count'] = bbb.groupby(['match_id', 'innings', 'striker_id'])['is_legal_delivery'].cumsum()
    # Balls faced before this delivery
    bbb['balls_faced_by_striker_before'] = bbb['striker_ball_count'] - bbb['is_legal_delivery']

    # --- Merge match metadata ---
    print("  Merging match metadata...")
    bbb = bbb.merge(
        matches_enriched[['match_id', 'comp_id', 'stage', 'knock_out', 'win_team_id',
                          'match_format', 'season', 'match_date']],
        on='match_id', how='left'
    )

    # Is this the batting team that won?
    bbb['batting_team_won'] = (bbb['batting_team_id'] == bbb['win_team_id']).astype(int)

    print(f"  Enriched ball-by-ball: {len(bbb)} deliveries across {bbb['match_id'].nunique()} matches")
    return bbb, matches_enriched


def load_and_prepare():
    """Main entry point: load everything and return enriched data."""
    print("Stage 1: Loading and preparing data...")
    bbb_raw, matches, competitions, playing_xi, mapping, teams = load_raw_data()
    bbb, matches_enriched = build_enriched_bbb(bbb_raw, matches, competitions)
    return bbb, matches_enriched, playing_xi, mapping, teams
