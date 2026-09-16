"""
Bankroll Growth Lab — Kelly, Autohedge, Arb & TKO staking tool.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from betting_math import (
    american_to_implied_prob,
    american_to_profit_ratio,
    arb_guaranteed_profit,
    autohedge_stake_b_fraction,
    balanced_arb_stake_b,
    eg_curve_vs_hedge,
    expected_log_growth,
    kelly_fraction,
    limit_stake_to_win,
    max_loss_fraction,
    optimal_hedge_kelly_style,
    remove_vig_two_way,
    stake_from_kelly,
    tko_allocation,
)

st.set_page_config(
    page_title="Bankroll Growth Lab",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .metric-box {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        padding: 1rem 1.25rem;
        border-radius: 0.75rem;
        border: 1px solid #0f3460;
    }
    .highlight { color: #e94560; font-weight: 600; }
    </style>
    """,
    unsafe_allow_html=True,
)


def fmt_pct(x: float, decimals: int = 2) -> str:
    return f"{x * 100:.{decimals}f}%"


def fmt_money(x: float) -> str:
    return f"${x:,.2f}"


def fmt_odds(x: float) -> str:
    if x >= 0:
        return f"+{x:.0f}"
    return f"{x:.0f}"


def odds_input(label: str, default: float, key: str) -> float:
    return st.number_input(
        label,
        value=float(default),
        step=5.0,
        format="%.0f",
        key=key,
        help="American odds (e.g. +400, -350)",
    )


def show_strategy_comparison(
    bankroll: float,
    odds_a: float,
    odds_b: float,
    p_a: float,
    stake_a: float,
    title: str,
):
    """Compare value, arb, autohedge, half-Kelly strategies."""
    p_b = 1.0 - p_a
    b_a = american_to_profit_ratio(odds_a)
    b_b = american_to_profit_ratio(odds_b)

    kelly_a = kelly_fraction(p_a, b_a)
    half_kelly_a = kelly_a / 2.0

    stake_a_full = min(stake_a, stake_from_kelly(bankroll, kelly_a))
    stake_a_half = stake_from_kelly(bankroll, half_kelly_a)

    stake_b_arb = balanced_arb_stake_b(stake_a, odds_a, odds_b)
    stake_b_auto = autohedge_stake_b_fraction(stake_a / bankroll, odds_a, odds_b, p_b) * bankroll

    strategies = {
        "Full Kelly (no hedge)": (stake_a_full, 0.0),
        "Half Kelly (no hedge)": (stake_a_half, 0.0),
        "Balanced Arb": (stake_a, stake_b_arb),
        "Autohedge (TKO)": (stake_a, stake_b_auto),
    }

    rows = []
    for name, (sa, sb) in strategies.items():
        sa_f, sb_f = sa / bankroll, sb / bankroll
        eg = expected_log_growth(sa_f, sb_f, odds_a, odds_b, p_a)
        ml = max_loss_fraction(sa_f, sb_f, odds_a, odds_b)
        mult_a, mult_b = (
            1.0 - sa_f - sb_f + sa_f * (1 + b_a),
            1.0 - sb_f - sa_f + sb_f * (1 + b_b),
        )
        profit_a = mult_a * bankroll - bankroll
        profit_b = mult_b * bankroll - bankroll
        rows.append(
            {
                "Strategy": name,
                "Stake A": fmt_money(sa),
                "Stake B": fmt_money(sb),
                "EG (log)": f"{eg:.6f}",
                "EG (bps)": f"{eg * 10000:.1f}",
                "Max Loss %": fmt_pct(ml),
                "Profit if A wins": fmt_money(profit_a),
                "Profit if B wins": fmt_money(profit_b),
            }
        )

    st.subheader(title)
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # EG curve
    max_hedge = balanced_arb_stake_b(stake_a, odds_a, odds_b) * 1.05 / bankroll
    hedge_fracs = np.linspace(0, max_hedge, 100)
    eg_line = eg_curve_vs_hedge(
        stake_a / bankroll, odds_a, odds_b, p_a, hedge_fracs
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hedge_fracs * 100,
            y=eg_line * 10000,
            mode="lines",
            name="EG vs hedge size",
            line=dict(color="#e94560", width=3),
        )
    )
    fig.add_vline(
        x=stake_b_auto / bankroll * 100,
        line_dash="dash",
        line_color="white",
        annotation_text="Autohedge",
    )
    fig.add_vline(
        x=stake_b_arb / bankroll * 100,
        line_dash="dot",
        line_color="#53d8fb",
        annotation_text="Balanced Arb",
    )
    fig.update_layout(
        title="Expected Log Growth vs Hedge Size on Team B",
        xaxis_title="Hedge stake (% of bankroll)",
        yaxis_title="EG (basis points)",
        template="plotly_dark",
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)


# ── Sidebar ──────────────────────────────────────────────────────────────────

with st.sidebar:
    st.title("📈 Bankroll Growth Lab")
    st.caption("Kelly · Autohedge · Arb · TKO")
    page = st.radio(
        "Tool",
        [
            "Soft vs Sharp (Autohedge)",
            "TKO Portfolio (Rufus' Demon)",
            "Hedge Existing Position",
            "Kelly Calculator",
            "Presets & Guide",
        ],
        label_visibility="collapsed",
    )
    st.divider()
    bankroll = st.number_input(
        "Total bankroll ($)",
        min_value=100.0,
        value=2500.0,
        step=100.0,
    )

# ── Pages ────────────────────────────────────────────────────────────────────

if page == "Soft vs Sharp (Autohedge)":
    st.header("Value Bet vs Arb vs Autohedge")
    st.markdown(
        """
        Line-shop a **soft book** (value side) against a **sharp book** (hedge side).
        When your value bet is limited, the optimal play is often **autohedging**:
        a balanced arb stake on the hedge side **plus** the (usually negative) Kelly
        fraction on that side — not full Kelly naked, and not a full scalp either.
        """
    )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Soft book (Team A — value)")
        odds_a_soft = odds_input("Team A moneyline", 400, "soft_a")
        max_win_soft = st.number_input(
            "Max to-win limit ($)", value=400.0, min_value=1.0, step=50.0
        )
        limit_stake_a = limit_stake_to_win(max_win_soft, odds_a_soft)
        st.info(f"Max stake on A at soft book: **{fmt_money(limit_stake_a)}**")

    with col2:
        st.subheader("Sharp book (Team B — hedge)")
        odds_b_sharp = odds_input("Team B moneyline", -350, "sharp_b")
        odds_a_sharp = odds_input("Team A at sharp (for vig-free line)", 315, "sharp_a")
        use_sharp_vig = st.checkbox("Derive true probs from sharp book", value=False)

    sharp_p_a, sharp_p_b = remove_vig_two_way(odds_a_sharp, odds_b_sharp)
    if use_sharp_vig:
        p_a, p_b = sharp_p_a, sharp_p_b
        st.caption(
            f"Vig-free from sharp book → Team A **{fmt_pct(p_a)}** · "
            f"Team B **{fmt_pct(p_b)}**"
        )
    else:
        p_a = st.slider(
            "True win prob — Team A",
            0.01,
            0.99,
            0.232,
            0.001,
            help="Chapter example uses 23.2% (±331 vig-free line)",
        )
        p_b = 1.0 - p_a
        st.caption(
            f"Sharp book devig reference: A **{fmt_pct(sharp_p_a)}** · "
            f"B **{fmt_pct(sharp_p_b)}**"
        )

    b_a = american_to_profit_ratio(odds_a_soft)
    kelly_a = kelly_fraction(p_a, b_a)
    kelly_b = kelly_fraction(p_b, american_to_profit_ratio(odds_b_sharp))

    stake_a = min(limit_stake_a, stake_from_kelly(bankroll, kelly_a))
    stake_b_arb = balanced_arb_stake_b(stake_a, odds_a_soft, odds_b_sharp)
    stake_b_auto = autohedge_stake_b_fraction(
        stake_a / bankroll, odds_a_soft, odds_b_sharp, p_b
    ) * bankroll
    arb_profit = arb_guaranteed_profit(
        stake_a, odds_a_soft, stake_b_arb, odds_b_sharp
    )

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Kelly stake on A", fmt_money(stake_from_kelly(bankroll, kelly_a)))
    m2.metric("Your stake on A (capped)", fmt_money(stake_a))
    m3.metric("Balanced arb on B", fmt_money(stake_b_arb))
    m4.metric("Autohedge on B", fmt_money(stake_b_auto))

    m5, m6, m7, m8 = st.columns(4)
    m5.metric("Kelly fraction A", fmt_pct(kelly_a))
    m6.metric("Kelly fraction B", fmt_pct(kelly_b))
    m7.metric("Arb guaranteed profit", fmt_money(arb_profit))
    m8.metric(
        "Autohedge max loss",
        fmt_pct(
            max_loss_fraction(
                stake_a / bankroll,
                stake_b_auto / bankroll,
                odds_a_soft,
                odds_b_sharp,
            )
        ),
    )

    st.success(
        f"**Recommended play:** Bet **{fmt_money(stake_a)}** on Team A at "
        f"{fmt_odds(odds_a_soft)}, then autohedge **{fmt_money(stake_b_auto)}** "
        f"on Team B at {fmt_odds(odds_b_sharp)} "
        f"({fmt_pct(stake_b_auto / bankroll)} of bankroll). "
        f"This beats a full arb by keeping skin in the game while cutting -EV hedge size."
    )

    show_strategy_comparison(
        bankroll,
        odds_a_soft,
        odds_b_sharp,
        p_a,
        stake_a,
        "Strategy Comparison",
    )

elif page == "TKO Portfolio (Rufus' Demon)":
    st.header("TKO Portfolio Allocation")
    st.markdown(
        """
        **Rufus' Demon** (Elihu Feustel): when you can bet *both* sides with no book
        limits, the growth-optimal split puts **f = p** of your bankroll on the +EV
        side and **1 − f** on the other — regardless of the specific odds.

        *Toy problem:* fair coin, heads **+300**, tails **-105** → bet **50% / 50%**.
        """
    )

    preset = st.selectbox(
        "Preset",
        [
            "Custom",
            "Fair coin (+300 / -105)",
            "Die roll (6 pays +700, else -550)",
            "Even-money soft/sharp (+100/-120 vs -120/+110)",
        ],
    )

    if preset == "Fair coin (+300 / -105)":
        odds_pos, odds_neg, p_pos = 300, -105, 0.5
    elif preset == "Die roll (6 pays +700, else -550)":
        odds_pos, odds_neg, p_pos = 700, -550, 1 / 6
    elif preset == "Even-money soft/sharp (+100/-120 vs -120/+110)":
        odds_pos, odds_neg, p_pos = 100, -120, 0.54  # approx vig-free
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            odds_pos = odds_input("+EV side odds", 300, "tko_pos")
        with c2:
            odds_neg = odds_input("-EV side odds", -105, "tko_neg")
        with c3:
            p_pos = st.number_input(
                "True win prob (+EV side)", 0.01, 0.99, 0.5, 0.001
            )

    f_pos, f_neg = tko_allocation(p_pos)
    b_pos = american_to_profit_ratio(odds_pos)
    b_neg = american_to_profit_ratio(odds_neg)

    stake_pos = bankroll * f_pos
    stake_neg = bankroll * f_neg

    kelly_pos = kelly_fraction(p_pos, b_pos)
    eg_tko = expected_log_growth(f_pos, f_neg, odds_pos, odds_neg, p_pos)
    eg_kelly_only = expected_log_growth(
        min(kelly_pos, 1.0), 0.0, odds_pos, odds_neg, p_pos
    )
    stake_b_arb = balanced_arb_stake_b(stake_pos, odds_pos, odds_neg)
    eg_arb = expected_log_growth(
        stake_pos / bankroll, stake_b_arb / bankroll, odds_pos, odds_neg, p_pos
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("TKO fraction (+EV)", fmt_pct(f_pos))
    c2.metric("TKO stake (+EV)", fmt_money(stake_pos))
    c3.metric("TKO stake (opposite)", fmt_money(stake_neg))
    c4.metric("EG (TKO, bps)", f"{eg_tko * 10000:.1f}")

    c5, c6 = st.columns(2)
    c5.metric("EG full Kelly only (bps)", f"{eg_kelly_only * 10000:.1f}")
    c6.metric("EG balanced arb (bps)", f"{eg_arb * 10000:.1f}")

    # Scan allocation fraction
    fracs = np.linspace(0.01, 0.99, 99)
    eg_scan = [
        expected_log_growth(f, 1 - f, odds_pos, odds_neg, p_pos) for f in fracs
    ]

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=fracs * 100,
            y=np.array(eg_scan) * 10000,
            mode="lines",
            line=dict(color="#53d8fb", width=3),
        )
    )
    fig.add_vline(
        x=f_pos * 100,
        line_dash="dash",
        line_color="#e94560",
        annotation_text=f"TKO optimum ({fmt_pct(f_pos)})",
    )
    fig.update_layout(
        title="Expected Log Growth vs Fraction on +EV Side",
        xaxis_title="Fraction on +EV side (%)",
        yaxis_title="EG (basis points)",
        template="plotly_dark",
        height=420,
    )
    st.plotly_chart(fig, use_container_width=True)

    mult_pos, mult_neg = (
        1 - f_pos - f_neg + f_pos * (1 + b_pos),
        1 - f_pos - f_neg + f_neg * (1 + b_neg),
    )
    st.dataframe(
        pd.DataFrame(
            [
                {
                    "Outcome": "+EV side wins",
                    "Wealth multiplier": f"{mult_pos:.4f}x",
                    "Final bankroll": fmt_money(mult_pos * bankroll),
                },
                {
                    "Outcome": "Opposite side wins",
                    "Wealth multiplier": f"{mult_neg:.4f}x",
                    "Final bankroll": fmt_money(mult_neg * bankroll),
                },
            ]
        ),
        hide_index=True,
        use_container_width=True,
    )

elif page == "Hedge Existing Position":
    st.header("Hedge an Existing Bet (Rufus Scenario)")
    st.markdown(
        """
        Already have money on the line? Only three things matter for the hedge:
        **hedge win probability**, **hedge odds**, and **how much your existing
        bets pay out (or cost you)** relative to bankroll.
        """
    )

    c1, c2 = st.columns(2)
    with c1:
        existing_profit_if_a = st.number_input(
            "Profit if existing side wins ($)", value=500.0, step=50.0
        )
        existing_loss_if_b = st.number_input(
            "Loss if existing side loses ($)", value=360000.0, step=1000.0,
            help="Total at risk if the outcome you're betting against happens",
        )
    with c2:
        hedge_odds = odds_input("Hedge odds (opposite side)", -150, "hedge_exist")
        p_hedge_wins = st.slider(
            "Prob hedge wins", 0.01, 0.99, 0.15, 0.01,
            help="Your estimate that the hedge side wins",
        )

    result = optimal_hedge_kelly_style(
        bankroll,
        existing_profit_if_a,
        existing_loss_if_b,
        hedge_odds,
        p_hedge_wins,
    )

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Optimal hedge stake", fmt_money(result["hedge_stake"]))
    c2.metric("Hedge % of bankroll", fmt_pct(result["hedge_fraction"]))
    c3.metric("Wealth if A wins", fmt_money(result["wealth_if_a_wins"]))
    c4.metric("Wealth if B wins", fmt_money(result["wealth_if_b_wins"]))

    c5, c6 = st.columns(2)
    c5.metric("Net P&L if existing wins", fmt_money(result["profit_if_a_wins"]))
    c6.metric("Net P&L if hedge wins", fmt_money(result["profit_if_b_wins"]))

    # Sweep hedge sizes
    hs = np.linspace(0, bankroll, 150)
    b = american_to_profit_ratio(hedge_odds)
    p = p_hedge_wins
    q = 1 - p
    eg_sweep = []
    for h in hs:
        w_a = bankroll + existing_profit_if_a - h
        w_b = bankroll + h * b - existing_loss_if_b
        if w_a <= 0 or w_b <= 0:
            eg_sweep.append(np.nan)
        else:
            eg_sweep.append(p * np.log(w_a) + q * np.log(w_b))

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=hs,
            y=np.array(eg_sweep),
            mode="lines",
            line=dict(color="#e94560", width=3),
        )
    )
    fig.add_vline(
        x=result["hedge_stake"],
        line_dash="dash",
        line_color="white",
        annotation_text="Optimal hedge",
    )
    fig.update_layout(
        title="Expected Log Growth vs Hedge Stake",
        xaxis_title="Hedge stake ($)",
        yaxis_title="E[log(wealth)]",
        template="plotly_dark",
        height=400,
    )
    st.plotly_chart(fig, use_container_width=True)

elif page == "Kelly Calculator":
    st.header("Kelly Criterion Calculator")
    st.markdown("Edge-over-odds form: **f\\* = (p·b − q) / b**")

    c1, c2, c3 = st.columns(3)
    with c1:
        odds = odds_input("American odds", 400, "kelly_odds")
    with c2:
        win_prob = st.number_input("True win probability", 0.01, 0.99, 0.232, 0.001)
    with c3:
        kelly_mult = st.select_slider(
            "Kelly multiplier",
            options=[0.25, 0.33, 0.5, 0.67, 1.0],
            value=1.0,
        )

    b = american_to_profit_ratio(odds)
    f = kelly_fraction(win_prob, b)
    f_adj = max(0.0, f * kelly_mult)
    edge = win_prob * b - (1 - win_prob)
    implied = american_to_implied_prob(odds)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Kelly fraction", fmt_pct(f))
    c2.metric(f"{kelly_mult} Kelly stake", fmt_money(bankroll * f_adj))
    c3.metric("Edge per $1", f"{edge:.4f}")
    c4.metric("Book implied prob", fmt_pct(implied))

    if f <= 0:
        st.warning("Negative Kelly — this is a -EV bet at your estimated probability.")

    st.subheader("Growth comparison by stake size")
    fracs = np.linspace(0, min(f * 1.5, 0.5) if f > 0 else 0.1, 80)
    fracs = fracs[fracs > 0]
    eg_vals = [
        win_prob * np.log(1 + frac * b) + (1 - win_prob) * np.log(1 - frac)
        for frac in fracs
    ]
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(x=fracs * 100, y=eg_vals, mode="lines", line=dict(width=3))
    )
    if f > 0:
        fig.add_vline(x=f * 100, line_dash="dash", annotation_text="Full Kelly")
    fig.update_layout(
        title="E[log(bankroll)] vs Stake Size",
        xaxis_title="Stake (% of bankroll)",
        yaxis_title="Expected log growth",
        template="plotly_dark",
        height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

else:  # Presets & Guide
    st.header("Presets & Quick Guide")
    st.markdown(
        """
        ### Core ideas from the chapter

        1. **Value betting** — one side is +EV; stake via Kelly.
        2. **Arbitrage** — both sides priced so you lock profit; no probability estimate needed.
        3. **Autohedge (TKO)** — bet the value side first (often at limits), then hedge
           on a sharp book at: **balanced arb stake + Kelly on hedge side** (Kelly is
           often negative, so you hedge *less* than a full scalp).
        4. **Rufus' Demon / TKO portfolio** — unlimited two-sided market: put **p**
           of bankroll on +EV side, **1−p** on the other.

        ### Chapter example (1H basketball)

        | | Soft book | Sharp book |
        |---|---|---|
        | Team A | +400 | +315 |
        | Team B | — | -350 |
        | Bankroll | $2,500 | |
        | Limit | $400 to win on A | |

        - Full Kelly on A ≈ **$100** (4% of bankroll)
        - Balanced arb hedge on B ≈ **$388** (15.5%) → **$11** locked profit
        - **Autohedge** on B ≈ **11%** of bankroll → higher EG than arb or naked Kelly

        ### When sharp book might be wrong

        If the true line equals the sharp line on the hedge side, autohedge still
        performs well; full Kelly without hedge is the worst case. When your value
        stake is only half-Kelly, a partial hedge can **eliminate risk** (freeroll).

        ### Deploy this tool

        Push to GitHub and deploy free on [Streamlit Community Cloud](https://share.streamlit.io):
        main file **`app.py`**, Python 3.10+.
        """
    )

    if st.button("Load chapter basketball preset"):
        st.session_state["preset_loaded"] = True
        st.info("Switch to **Soft vs Sharp (Autohedge)** in the sidebar — defaults match the chapter.")

st.divider()
st.caption(
    "Educational tool only. Not financial advice. Gamble responsibly where legal."
)
