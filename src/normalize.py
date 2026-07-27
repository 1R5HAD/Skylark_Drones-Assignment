"""
Turns raw monday.com board payloads into clean pandas DataFrames.

Handles the specific messiness seen in the sample data:
- Stray rows where a cell's value duplicates its own column header
  (leftover header rows pasted into the sheet).
- Inconsistent/blank date, sector, and amount fields.
- Masked currency fields that still need numeric parsing.

Every normalize_* function returns (DataFrame, caveats: list[str]) so
callers (the agent) can surface data-quality issues to the user
instead of silently guessing.
"""

from __future__ import annotations
import pandas as pd

DATE_LIKE_KEYWORDS = ("date", "month")
AMOUNT_LIKE_KEYWORDS = ("amount", "value", "billed", "collected")


def _items_to_raw_df(board_payload: dict) -> pd.DataFrame:
    rows = []
    for item in board_payload["items"]:
        row = {"item_name": item["name"]}
        for cv in item["column_values"]:
            title = cv["column"]["title"]
            row[title] = cv["text"]
        rows.append(row)
    return pd.DataFrame(rows)


def _drop_stray_header_rows(df: pd.DataFrame) -> tuple[pd.DataFrame, int]:
    """Drop rows where >=3 cells equal their own column name (pasted header rows)."""
    def is_header_echo(row):
        matches = sum(1 for col, val in row.items() if isinstance(val, str) and val.strip() == col)
        return matches >= 3

    mask = df.apply(is_header_echo, axis=1)
    dropped = int(mask.sum())
    return df.loc[~mask].reset_index(drop=True), dropped


def _coerce_dates(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if any(k in col.lower() for k in DATE_LIKE_KEYWORDS):
            df[col] = pd.to_datetime(df[col], errors="coerce", format="mixed")
    return df


def _coerce_amounts(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        if any(k in col.lower() for k in AMOUNT_LIKE_KEYWORDS):
            cleaned = (
                df[col]
                .astype(str)
                .str.replace(r"[^\d.\-]", "", regex=True)
                .replace("", pd.NA)
            )
            df[col] = pd.to_numeric(cleaned, errors="coerce")
    return df


def _standardize_text(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"": pd.NA, "nan": pd.NA, "None": pd.NA})
    return df


def normalize_board(board_payload: dict) -> tuple[pd.DataFrame, list[str]]:
    caveats = []
    df = _items_to_raw_df(board_payload)

    df, dropped = _drop_stray_header_rows(df)
    if dropped:
        caveats.append(f"Dropped {dropped} stray row(s) that duplicated the header instead of holding data.")

    df = _standardize_text(df)
    df = _coerce_dates(df)
    df = _coerce_amounts(df)

    null_summary = df.isna().mean().sort_values(ascending=False)
    heavy_null_cols = null_summary[null_summary > 0.4]
    if not heavy_null_cols.empty:
        cols = ", ".join(f"{c} ({p:.0%} blank)" for c, p in heavy_null_cols.items())
        caveats.append(f"Columns with heavy missing data: {cols}.")

    return df, caveats
