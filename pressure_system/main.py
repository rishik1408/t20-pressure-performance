"""
Main entry point for the Enhanced Equalized Pressure Performance System.
Executes the 5-Pillar Architectural Framework:
  1. Phase-Normalized Dynamic Pressure Index (P-NPI)
  2. Competition Tier Indexing (IPL 1.30x, Tier-1 Bilaterals 1.10x, Associate 0.75x)
  3. Opposition Quality Weighting (Live Elo & Bowler Matchup xV)
  4. Rate Efficiency + Volume Value Balance
  5. Master Top 10 & Role-Segregated Dropdown Leaderboards
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pressure_system.data_loader import load_and_prepare
from pressure_system.win_probability import run_win_probability
from pressure_system.pressure_index import compute_pressure_index
from pressure_system.opposition_quality import enrich_matchup_multipliers
from pressure_system.phase_benchmarking import (compute_phase_xruns,
                                                compute_anchoring_and_entry_baselines,
                                                compute_phase_relative_metrics)
from pressure_system.player_metrics import run_player_metrics
from pressure_system.generate_report import run_report_generation


def main():
    start_time = time.time()
    print("=" * 75)
    print("ENHANCED 5-PILLAR CLUTCH PERFORMANCE SYSTEM (MASTER + ROLE LEADERBOARDS)")
    print("=" * 75)
    print()

    # Stage 1: Load and prepare data
    bbb, matches, playing_xi, mapping, teams = load_and_prepare()
    print()

    # Stage 2: Win Probability Model
    bbb, wp_model, calibration_data = run_win_probability(bbb)
    print()

    # Stage 3: Phase-Normalized Dynamic Pressure Index (P-NPI)
    bbb = compute_pressure_index(bbb)
    print()

    # Stage 4A: Opposition Quality Weighting & Competition Tier Indexing
    bbb, final_elos = enrich_matchup_multipliers(bbb, matches)
    print()

    # Stage 4B: Phase-Relative Benchmarking (xRuns, Entry-Points, Anchoring)
    bbb = compute_phase_xruns(bbb)
    bbb, stints, anchoring_summary = compute_anchoring_and_entry_baselines(bbb)
    prva_df = compute_phase_relative_metrics(bbb)
    print()

    # Stage 4C: Player Metrics & Composite Equalized Clutch Scores
    bat_metrics, bowl_metrics, bat_ranked, bowl_ranked, role_rankings = run_player_metrics(
        bbb, anchoring_summary=anchoring_summary, prva_df=prva_df
    )
    print()

    # Print Master Top 10 Batters
    print("=" * 75)
    print("MASTER TOP 10 CLUTCH BATTERS (ALL ROLES EQUALIZED)")
    print("=" * 75)
    for _, r in bat_ranked.head(10).iterrows():
        print(f"  #{int(r['rank']):2d}  {r['player_name']:<24s} ({r['primary_role']:<24s})  "
              f"Score: {r['clutch_score']:5.1f}  "
              f"HP Balls: {int(r['hp_balls']):4d}  "
              f"HP SR: {r['hp_sr']:5.1f}  "
              f"DropOff: {r['drop_off_ratio']:4.2f}")
    print()

    # Print Master Top 10 Bowlers
    print("=" * 75)
    print("MASTER TOP 10 CLUTCH BOWLERS (ALL ROLES EQUALIZED)")
    print("=" * 75)
    for _, r in bowl_ranked.head(10).iterrows():
        print(f"  #{int(r['rank']):2d}  {r['player_name']:<24s} ({r['primary_role']:<24s})  "
              f"Score: {r['clutch_score']:5.1f}  "
              f"HP Balls: {int(r['hp_balls']):4d}  "
              f"HP Econ: {r['hp_econ']:4.2f}  "
              f"DropOff: {r['bowling_drop_off']:4.2f}")
    print()

    # Print Role Dropdowns
    print("=" * 75)
    print("ROLE-SEGREGATED DROPDOWNS (TOP 5 PER MATCH PHASE)")
    print("=" * 75)
    print("\n[BATTING] 1. Top-Order Anchors & Powerplay Enforcers:")
    for _, r in role_rankings['bat_top_order'].iterrows():
        print(f"   #{int(r['role_rank'])} {r['player_name']:<22s} | Balls: {int(r['balls_faced']):4d} | HP SR: {r['hp_sr']:5.1f} | DropOff: {r['drop_off_ratio']:.2f} | Score: {r['clutch_score']:.1f}")

    print("\n[BATTING] 2. Middle-Order Engines & Rebuilders:")
    for _, r in role_rankings['bat_middle'].iterrows():
        print(f"   #{int(r['role_rank'])} {r['player_name']:<22s} | Balls: {int(r['balls_faced']):4d} | HP SR: {r['hp_sr']:5.1f} | DropOff: {r['drop_off_ratio']:.2f} | Score: {r['clutch_score']:.1f}")

    print("\n[BATTING] 3. Death-Overs Finishers:")
    for _, r in role_rankings['bat_death'].iterrows():
        print(f"   #{int(r['role_rank'])} {r['player_name']:<22s} | Balls: {int(r['balls_faced']):4d} | HP SR: {r['hp_sr']:5.1f} | DropOff: {r['drop_off_ratio']:.2f} | Score: {r['clutch_score']:.1f}")

    print("\n[BOWLING] 1. Powerplay Strike Bowlers:")
    for _, r in role_rankings['bowl_pp'].iterrows():
        print(f"   #{int(r['role_rank'])} {r['player_name']:<22s} | Balls: {int(r['balls_bowled']):4d} | HP Econ: {r['hp_econ']:4.2f} | DropOff: {r['bowling_drop_off']:.2f} | Score: {r['clutch_score']:.1f}")

    print("\n[BOWLING] 2. Middle-Overs Choke & Spin Enforcers:")
    for _, r in role_rankings['bowl_mid'].iterrows():
        print(f"   #{int(r['role_rank'])} {r['player_name']:<22s} | Balls: {int(r['balls_bowled']):4d} | HP Econ: {r['hp_econ']:4.2f} | DropOff: {r['bowling_drop_off']:.2f} | Score: {r['clutch_score']:.1f}")

    print("\n[BOWLING] 3. Death-Overs Specialists:")
    for _, r in role_rankings['bowl_death'].iterrows():
        print(f"   #{int(r['role_rank'])} {r['player_name']:<22s} | Balls: {int(r['balls_bowled']):4d} | HP Econ: {r['hp_econ']:4.2f} | DropOff: {r['bowling_drop_off']:.2f} | Score: {r['clutch_score']:.1f}")
    print()

    # Stage 5: Generate Report, Charts, Rankings
    report_path = run_report_generation(
        bbb, bat_metrics, bowl_metrics, bat_ranked, bowl_ranked,
        role_rankings, calibration_data, final_elos, teams
    )
    print()

    elapsed = time.time() - start_time
    print("=" * 75)
    print(f"PIPELINE COMPLETE in {elapsed:.1f} seconds")
    print(f"  Report: {report_path}")
    print(f"  Charts: {os.path.join(os.path.dirname(report_path), 'charts')}")
    print("=" * 75)


if __name__ == '__main__':
    main()
