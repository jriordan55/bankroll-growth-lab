"""Kelly criterion, arbitrage, autohedge, and TKO portfolio math."""

from __future__ import annotations

import numpy as np


def american_to_profit_ratio(american: float) -> float:
    """Net profit per $1 staked (Kelly b parameter)."""
    if american == 0:
        raise ValueError("American odds cannot be zero.")
    if american > 0:
        return american / 100.0
    return 100.0 / abs(american)


def american_to_implied_prob(american: float) -> float:
    """Implied win probability from American odds (includes vig)."""
    if american > 0:
        return 100.0 / (american + 100.0)
    return abs(american) / (abs(american) + 100.0)


def remove_vig_two_way(odds_a: float, odds_b: float) -> tuple[float, float]:
    """Return vig-free win probabilities for a two-way market."""
    p_a = american_to_implied_prob(odds_a)
    p_b = american_to_implied_prob(odds_b)
    total = p_a + p_b
    if total <= 0:
        raise ValueError("Invalid odds supplied.")
    return p_a / total, p_b / total


def kelly_fraction(p: float, b: float) -> float:
    """
    Kelly fraction of bankroll to stake.
    p = true win probability, b = net profit per $1 staked.
    Negative values indicate -EV (useful for autohedge adjustments).
    """
    q = 1.0 - p
    return (p * b - q) / b


def stake_from_kelly(bankroll: float, fraction: float) -> float:
    return max(0.0, bankroll * fraction)


def balanced_arb_stake_b(
    stake_a: float,
    odds_a: float,
    odds_b: float,
) -> float:
    """
    Stake on side B to balance a two-leg arb given fixed stake on side A.
    Returns equal profit regardless of which side wins (before rounding).
    """
    b_a = american_to_profit_ratio(odds_a)
    b_b = american_to_profit_ratio(odds_b)
    # Profit if A wins: stake_a * b_a - stake_b
    # Profit if B wins: stake_b * b_b - stake_a
    # stake_a * b_a - s = s * b_b - stake_a  =>  s = stake_a * (1 + b_a) / (1 + b_b) ... 
    # Correct balance: stake_a * b_a - s = s * b_b - stake_a
    # stake_a * (b_a + 1) = s * (b_b + 1)  => profit = stake_a * b_a - s
    s = stake_a * (b_a + 1) / (b_b + 1)
    return s


def arb_guaranteed_profit(
    stake_a: float,
    odds_a: float,
    stake_b: float,
    odds_b: float,
) -> float:
    """Guaranteed profit from a balanced two-way arb."""
    b_a = american_to_profit_ratio(odds_a)
    b_b = american_to_profit_ratio(odds_b)
    profit_a = stake_a * b_a - stake_b
    profit_b = stake_b * b_b - stake_a
    return (profit_a + profit_b) / 2.0


def wealth_multipliers_two_bet(
    stake_a_frac: float,
    stake_b_frac: float,
    odds_a: float,
    odds_b: float,
    p_a_wins: float,
) -> tuple[float, float]:
    """
    Return (multiplier_if_a_wins, multiplier_if_b_wins) as fractions of bankroll
    after both bets are placed. stake_* are fractions of starting bankroll.
    """
    b_a = american_to_profit_ratio(odds_a)
    b_b = american_to_profit_ratio(odds_b)
    total_staked = stake_a_frac + stake_b_frac
    if total_staked > 1.0 + 1e-9:
        raise ValueError("Total stake exceeds bankroll.")

    mult_a = 1.0 - total_staked + stake_a_frac * (1.0 + b_a)
    mult_b = 1.0 - total_staked + stake_b_frac * (1.0 + b_b)
    return mult_a, mult_b


def expected_log_growth(
    stake_a_frac: float,
    stake_b_frac: float,
    odds_a: float,
    odds_b: float,
    p_a_wins: float,
) -> float:
    """E[log(W)] for a two-outcome portfolio."""
    mult_a, mult_b = wealth_multipliers_two_bet(
        stake_a_frac, stake_b_frac, odds_a, odds_b, p_a_wins
    )
    p_b = 1.0 - p_a_wins
    if mult_a <= 0 or mult_b <= 0:
        return float("-inf")
    return p_a_wins * np.log(mult_a) + p_b * np.log(mult_b)


def autohedge_stake_b_fraction(
    stake_a_frac: float,
    odds_a: float,
    odds_b: float,
    p_b_wins: float,
) -> float:
    """
    TKO autohedge: balanced arb hedge on B plus Kelly adjustment (often negative).
    When side A is limited/maxed, reduce B stake below full arb by Kelly on B.
    """
    if stake_a_frac <= 0:
        return max(0.0, kelly_fraction(p_b_wins, american_to_profit_ratio(odds_b)))

    stake_b_arb = balanced_arb_stake_b(
        stake_a_frac, odds_a, odds_b
    )  # as fraction if bankroll=1
    kelly_b = kelly_fraction(p_b_wins, american_to_profit_ratio(odds_b))
    return max(0.0, stake_b_arb + kelly_b)


def max_loss_fraction(
    stake_a_frac: float,
    stake_b_frac: float,
    odds_a: float,
    odds_b: float,
) -> float:
    """Maximum bankroll loss fraction across outcomes."""
    mult_a, mult_b = wealth_multipliers_two_bet(
        stake_a_frac, stake_b_frac, odds_a, odds_b, 0.5
    )
    return max(0.0, 1.0 - min(mult_a, mult_b))


def tko_allocation(p_positive_ev: float) -> tuple[float, float]:
    """
    Rufus' Demon / TKO: fraction on +EV side = true probability,
    remainder on opposite side.
    """
    p = min(max(p_positive_ev, 0.0), 1.0)
    return p, 1.0 - p


def hedge_existing_position(
    bankroll: float,
    existing_payout_if_win: float,
    hedge_odds: float,
    p_hedge_wins: float,
) -> dict:
    """
    Optimal hedge stake when you already have a position (Rufus scenario).
    Maximizes E[log(wealth)] for an additional hedge bet.
    """
    b = american_to_profit_ratio(hedge_odds)
    p = p_hedge_wins
    q = 1.0 - p

    # Wealth multipliers: W_win = bankroll + existing_payout - h
    # W_lose = bankroll - h + h*(1+b) = bankroll + h*b
    # Actually existing bet: if hedge wins, existing loses (typical hedge)
    # Model: if hedge wins (B wins), existing A bet loses stake but we care about
    # net P&L relative to bankroll.

    # General: existing position adds `existing_payout_if_win` if favored side wins,
    # and `-existing_at_risk` if it loses. User provides net payout if hedge wins vs loses.

    def eg(h: float) -> float:
        if h < 0 or h > bankroll:
            return float("-inf")
        # Hedge wins: existing bet loses (assume full loss of opposing exposure)
        w_win = bankroll - h  # simplified: user inputs net outcomes below
        w_lose = bankroll - h + h * (1 + b)
        if w_win <= 0 or w_lose <= 0:
            return float("-inf")
        return p * np.log(w_win) + q * np.log(w_lose)

    # Better model from chapter: existing bet pays out `existing_payout_if_win`
    # (profit) if team A wins; if B wins, lose existing stake (embedded in bankroll).

    def eg_hedge(h: float, existing_profit_if_a: float, existing_loss_if_b: float) -> float:
        if h < 0 or h > bankroll:
            return float("-inf")
        # B wins (hedge wins): profit = h*b - existing_loss_if_b
        w_b = bankroll + h * b - existing_loss_if_b
        # A wins (hedge loses): profit = existing_profit_if_a - h
        w_a = bankroll + existing_profit_if_a - h
        if w_a <= 0 or w_b <= 0:
            return float("-inf")
        return p * np.log(w_a) + q * np.log(w_b)

    return {"optimize": eg_hedge}


def optimal_hedge_kelly_style(
    bankroll: float,
    existing_profit_if_a: float,
    existing_loss_if_b: float,
    hedge_odds: float,
    p_hedge_wins: float,
    grid_points: int = 2000,
) -> dict:
    """Find hedge maximizing log growth via numerical search."""
    b = american_to_profit_ratio(hedge_odds)
    p = p_hedge_wins
    q = 1.0 - p

    best_h = 0.0
    best_eg = float("-inf")

    for h in np.linspace(0, bankroll, grid_points):
        w_b = bankroll + h * b - existing_loss_if_b
        w_a = bankroll + existing_profit_if_a - h
        if w_a <= 0 or w_b <= 0:
            continue
        eg = p * np.log(w_a) + q * np.log(w_b)
        if eg > best_eg:
            best_eg = eg
            best_h = h

    w_a = bankroll + existing_profit_if_a - best_h
    w_b = bankroll + best_h * b - existing_loss_if_b

    return {
        "hedge_stake": best_h,
        "hedge_fraction": best_h / bankroll if bankroll else 0,
        "expected_log_growth": best_eg,
        "wealth_if_a_wins": w_a,
        "wealth_if_b_wins": w_b,
        "profit_if_a_wins": existing_profit_if_a - best_h,
        "profit_if_b_wins": best_h * b - existing_loss_if_b,
    }


def eg_curve_vs_hedge(
    stake_a_frac: float,
    odds_a: float,
    odds_b: float,
    p_a_wins: float,
    hedge_fracs: np.ndarray,
) -> np.ndarray:
    """EG when stake on A is fixed and stake on B varies."""
    return np.array(
        [
            expected_log_growth(stake_a_frac, h, odds_a, odds_b, p_a_wins)
            for h in hedge_fracs
        ]
    )


def limit_stake_to_win(max_win: float, odds: float) -> float:
    """Max stake given a cap on potential profit (to-win limit)."""
    b = american_to_profit_ratio(odds)
    if b <= 0:
        raise ValueError("Cannot compute to-win limit for non-positive odds.")
    return max_win / b
