# Bankroll Growth Lab

Streamlit betting tool for **Kelly criterion**, **autohedging (TKO)**, **arbitrage**, and **hedging existing positions** — based on value-bet vs arb vs autohedge bankroll growth analysis.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open http://localhost:8501

## Deploy a public URL (Streamlit Cloud)

1. Push this folder to a GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io) and sign in with GitHub.
3. **New app** → select your repo → main file: `app.py`.
4. Deploy. You get a URL like `https://your-app-name.streamlit.app`.

## Tools included

| Tab | Purpose |
|-----|---------|
| Soft vs Sharp | Autohedge sizing when value side is limited |
| TKO Portfolio | Rufus' Demon optimal two-sided allocation |
| Hedge Existing | Optimal hedge for an open position (Rufus scenario) |
| Kelly Calculator | Single-bet Kelly with fractional sizing |
| Presets & Guide | Chapter examples and deployment notes |
