# Bankroll Growth Lab

Streamlit betting tool for **Kelly criterion**, **autohedging (TKO)**, **arbitrage**, and **hedging existing positions** — based on value-bet vs arb vs autohedge bankroll growth analysis.

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://bankroll-growth-lab.streamlit.app)

**Live app:** [https://bankroll-growth-lab.streamlit.app](https://bankroll-growth-lab.streamlit.app)  
**Repo:** [github.com/jriordan55/bankroll-growth-lab](https://github.com/jriordan55/bankroll-growth-lab)

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

## Deploy on Streamlit Cloud

**[One-click deploy →](https://share.streamlit.io/deploy?repository=jriordan55/bankroll-growth-lab&branch=main&mainModule=app.py&subdomain=bankroll-growth-lab)**

1. Open the link above and sign in with GitHub (**jriordan55**).
2. Confirm repo `jriordan55/bankroll-growth-lab`, branch `main`, file `app.py`.
3. Click **Deploy** → live at `https://bankroll-growth-lab.streamlit.app`.

## Tools included

| Tab | Purpose |
|-----|---------|
| Soft vs Sharp | Autohedge sizing when value side is limited |
| TKO Portfolio | Rufus' Demon optimal two-sided allocation |
| Hedge Existing | Optimal hedge for an open position (Rufus scenario) |
| Kelly Calculator | Single-bet Kelly with fractional sizing |
| Presets & Guide | Chapter examples and deployment notes |
