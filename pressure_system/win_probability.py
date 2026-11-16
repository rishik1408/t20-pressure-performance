"""
Stage 2: Win Probability Model
Trains a logistic regression model on match state features to predict
batting team win probability, then computes WPA for every delivery.
"""

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import PolynomialFeatures, StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.calibration import calibration_curve
import warnings
warnings.filterwarnings('ignore')


def build_features(bbb, state='before'):
    """
    Build feature matrix for Win Probability model.
    state='before' uses pre-delivery state, 'after' uses post-delivery state.
    """
    suffix = '_before' if state == 'before' else '_after' if state == 'after' else ''

    features = pd.DataFrame(index=bbb.index)

    # Common features
    features['innings'] = (bbb['innings'] == 2).astype(int)
    features['balls_remaining'] = bbb[f'balls_remaining{suffix}']
    features['wickets_in_hand'] = bbb[f'wickets_in_hand{suffix}']
    features['runs_scored'] = bbb[f'total_runs{"_before" if state == "before" else "_so_far"}']

    # Run rate (use before for both states to avoid division issues)
    overs = bbb[f'overs_bowled{"_before" if state == "before" else "_after"}']
    runs = bbb[f'total_runs{"_before" if state == "before" else "_so_far"}']
    features['current_run_rate'] = np.where(overs > 0, runs / overs, 0.0)

    # 2nd innings features
    is_2nd = bbb['innings'] == 2
    if state == 'before':
        features['runs_required'] = np.where(is_2nd, bbb['runs_required_before'], 0)
        features['rrr'] = np.where(is_2nd, bbb['rrr_before'].fillna(0), 0)
    else:
        features['runs_required'] = np.where(is_2nd, bbb['runs_required_after'], 0)
        overs_rem = bbb['balls_remaining_after'] / 6.0
        features['rrr'] = np.where(
            is_2nd & (overs_rem > 0),
            bbb['runs_required_after'] / overs_rem,
            np.where(is_2nd, 99.0, 0)  # infinite RRR if no balls left
        )

    features['rrr_minus_crr'] = np.where(is_2nd, features['rrr'] - features['current_run_rate'], 0)

    # Interaction: wickets * balls remaining (captures "enough resources" concept)
    features['resources'] = features['wickets_in_hand'] * features['balls_remaining']

    # Clean up any infinities or NaNs
    features = features.replace([np.inf, -np.inf], 99.0).fillna(0)

    return features


def train_wp_model(bbb):
    """
    Train a Win Probability model on the ball-by-ball data.
    Returns the fitted pipeline.
    """
    print("  Training Win Probability model...")

    # Build features from "before" state
    X = build_features(bbb, state='before')
    y = bbb['batting_team_won'].values

    # Pipeline: StandardScaler -> PolynomialFeatures -> LogisticRegression
    pipeline = Pipeline([
        ('scaler', StandardScaler()),
        ('poly', PolynomialFeatures(degree=2, interaction_only=True, include_bias=False)),
        ('lr', LogisticRegression(C=1.0, max_iter=1000, solver='lbfgs'))
    ])

    pipeline.fit(X, y)

    # Evaluate calibration
    y_pred_prob = pipeline.predict_proba(X)[:, 1]
    fraction_pos, mean_predicted = calibration_curve(y, y_pred_prob, n_bins=10, strategy='quantile')

    print("  Win Probability Model Calibration:")
    for mp, fp in zip(mean_predicted, fraction_pos):
        print(f"    Predicted: {mp:.3f}  Actual: {fp:.3f}")

    # Brier score
    brier = np.mean((y_pred_prob - y) ** 2)
    print(f"  Brier Score: {brier:.4f}")

    return pipeline, {'fraction_pos': fraction_pos, 'mean_predicted': mean_predicted, 'brier': brier}


def compute_wpa(bbb, model):
    """
    Compute Win Probability Added for every delivery.
    WPA = WP_after - WP_before (from batting team's perspective).
    """
    print("  Computing Win Probability Added for all deliveries...")

    # Get WP before each delivery
    X_before = build_features(bbb, state='before')
    wp_before = model.predict_proba(X_before)[:, 1]

    # Get WP after each delivery
    X_after = build_features(bbb, state='after')
    wp_after = model.predict_proba(X_after)[:, 1]

    # Handle end-of-innings edge cases
    # If 2nd innings and batting team passed the target -> WP = 1.0
    is_2nd = bbb['innings'] == 2
    passed_target = is_2nd & (bbb['runs_required_after'] <= 0)
    wp_after = np.where(passed_target, 1.0, wp_after)

    # If all out (10 wickets) and not passed target -> WP depends on innings
    all_out = bbb['wickets_in_hand_after'] <= 0
    # In 2nd innings, all out without reaching target -> WP = 0
    wp_after = np.where(is_2nd & all_out & ~passed_target, 0.0, wp_after)

    # If 2nd innings, last ball, and target not reached -> WP = 0
    last_ball_2nd = is_2nd & (bbb['balls_remaining_after'] <= 0) & (bbb['runs_required_after'] > 0)
    wp_after = np.where(last_ball_2nd, 0.0, wp_after)

    bbb = bbb.copy()
    bbb['wp_before'] = wp_before
    bbb['wp_after'] = wp_after
    bbb['wpa_batting'] = wp_after - wp_before  # positive = good for batting team
    bbb['wpa_bowling'] = -(wp_after - wp_before)  # positive = good for bowling/fielding team

    # Sanity check: sum WPA per match per innings
    wpa_by_match = bbb.groupby(['match_id'])['wpa_batting'].sum()
    print(f"  WPA sum stats across matches: mean={wpa_by_match.mean():.3f}, std={wpa_by_match.std():.3f}")

    return bbb


def run_win_probability(bbb):
    """Main entry point for Stage 2."""
    print("Stage 2: Win Probability Model...")
    model, calibration_data = train_wp_model(bbb)
    bbb = compute_wpa(bbb, model)
    return bbb, model, calibration_data
