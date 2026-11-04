"""Génère des séries SYNTHÉTIQUES pour tester le pipeline hors ligne (jamais publiées comme réelles)."""
import sys
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config as cfg  # noqa: E402

rng = np.random.default_rng(42)
out = Path(sys.argv[1]) / "raw"
out.mkdir(parents=True, exist_ok=True)
end = pd.Timestamp.today().normalize()

LEVELS = {  # (niveau, volatilité relative quotidienne, fréquence)
    "gdp": (100, 0.004, "QS"), "cpi": (100, 0.002, "MS"), "unemp": (7, 0.02, "MS"), "cli": (100, 0.003, "MS"),
    "esi": (100, 0.01, "MS"), "climat": (100, 0.01, "MS"), "fed_funds": (2.5, 0.01, "D"), "ecb_dfr": (1, 0.01, "D"),
    "2y": (2.5, 0.01, "B"), "10y": (3, 0.008, "B"), "oat": (2.5, 0.01, "MS"), "bund": (1.8, 0.01, "MS"),
    "price": (1000, 0.011, "B"), "eurusd": (1.15, 0.004, "B"), "dxy": (98, 0.004, "B"), "cape": (28, 0.02, "MS"),
    "pe": (22, 0.02, "MS"), "vix": (18, 0.05, "B"), "vstoxx": (20, 0.05, "B"), "hy": (4.5, 0.015, "B"),
    "gpr": (100, 0.08, "D"), "epu": (150, 0.06, "MS"), "credit": (150, 0.004, "QS"), "nfci": (-0.4, 0.02, "W"),
    "ciss": (0.15, 0.04, "B"),
}

def kind(name):
    for k in ["fed_funds", "ecb_dfr", "eurusd", "dxy", "cape", "vstoxx", "vix", "nfci", "ciss", "gpr", "climat", "esi", "oat", "bund"]:
        if k in name:
            return k
    for k, ks in [("gdp", ["gdp"]), ("cpi", ["cpi", "hicp"]), ("unemp", ["unemp"]), ("cli", ["cli_"]),
                  ("2y", ["_2y"]), ("10y", ["_10y"]), ("pe", ["_pe"]), ("hy", ["_hy"]), ("epu", ["epu"]),
                  ("credit", ["credit"])]:
        if any(x in name for x in ks):
            return k
    return "price"

for name in cfg.SERIES:
    lvl, vol, freq = LEVELS[kind(name)]
    idx = pd.date_range("1995-01-01", end, freq=freq)
    if kind(name) in ("gdp", "cpi", "credit", "price"):
        drift = 0.00025 if freq == "B" else 0.006
        x = lvl * np.exp(np.cumsum(rng.normal(drift, vol * (5 if freq != "B" else 1), len(idx))))
    else:
        x = np.empty(len(idx)); x[0] = lvl
        for i in range(1, len(idx)):  # processus à retour vers la moyenne
            x[i] = x[i-1] + 0.02 * (lvl - x[i-1]) + rng.normal(0, abs(lvl) * vol + 0.01)
    pd.Series(x, index=idx, name="value").rename_axis("date").to_csv(out / f"{name}.csv")
    (out / f"{name}.src").write_text(cfg.SERIES[name]["src"][0][0])
print("fixtures écrites dans", out)
