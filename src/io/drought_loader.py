from __future__ import annotations
import pandas as pd
from pathlib import Path

from src.risk.risk_engine import DroughtSignals

DATA_PATH = Path(__file__).resolve().parents[2] / "data" / "derived" / "drought_signals.csv"

def load_drought_table(path: Path = DATA_PATH) -> pd.DataFrame:
    df = pd.read_csv(path)
    required = {"date", "region", "spi12", "spi24", "cdi"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing columns in drought_signals.csv: {missing}")
    return df

def pick_signals(df: pd.DataFrame, month: int, region: str = "Ege") -> DroughtSignals:
    df_r = df[df["region"] == region].copy()
    if df_r.empty:
        raise ValueError(f"No rows found for region={region}")

    df_r["month"] = df_r["date"].astype(str).str.split("-").str[1].astype(int)
    hit = df_r[df_r["month"] == month]
    if hit.empty:
        hit = df_r.sort_values("date").tail(1)

    row = hit.iloc[0]
    return DroughtSignals(
        spi12=float(row["spi12"]),
        spi24=float(row["spi24"]),
        cdi=str(row["cdi"]).strip().lower(),
    )
