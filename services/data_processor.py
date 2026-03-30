"""Data processing utilities for Graas Command Center."""

import pandas as pd
import numpy as np
from typing import Tuple


# ── Hoppr Processing ─────────────────────────────────────────────────────────

def process_hoppr_daily(df: pd.DataFrame) -> pd.DataFrame:
    """Process Hoppr daily analysis data.

    The CSV has headers on row 4 (0-indexed 3), with data in columns B-I.
    Two side-by-side tables: daily (left) and country (right).
    """
    if df.empty:
        return df

    # Find the header row containing 'DATE' and 'TOTAL_NO_OF_QUERIES'
    header_row = None
    for idx, row in df.iterrows():
        vals = [str(v).strip() for v in row.values]
        if "DATE" in vals and "TOTAL_NO_OF_QUERIES" in vals:
            header_row = idx
            break

    if header_row is None:
        return pd.DataFrame()

    # Extract data below the header row
    data_df = df.iloc[header_row + 1:].copy()
    headers = [str(v).strip() for v in df.iloc[header_row].values]

    # Find the DATE column index for the daily table (first occurrence)
    date_idx = headers.index("DATE")

    # Daily columns: DATE through LOGGED_IN_SELLER_FROM_HOPPR
    daily_col_names = ["DATE", "TOTAL_NO_OF_QUERIES", "UNIQUE_USERS", "TOTAL_UNIQUE_SELLERS",
                       "REPEAT_GUEST_USERS", "NEW_SIGNUPS", "LOGGED_IN_SELLER_FROM_TC",
                       "LOGGED_IN_SELLER_FROM_HOPPR"]
    daily_indices = []
    for name in daily_col_names:
        if name in headers:
            daily_indices.append(headers.index(name))

    if not daily_indices:
        return pd.DataFrame()

    result = data_df.iloc[:, daily_indices].copy()
    result.columns = ["date", "total_queries", "unique_users", "unique_sellers",
                       "repeat_guests", "new_signups", "login_from_tc", "login_from_hoppr"][:len(daily_indices)]

    # Clean — filter out empty rows
    result["date"] = result["date"].astype(str).str.strip()
    result = result[result["date"] != ""].copy()
    result = result[result["date"] != "nan"].copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result = result.dropna(subset=["date"])

    for col in result.columns[1:]:
        result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0).astype(int)

    return result.sort_values("date").reset_index(drop=True)


def process_hoppr_country(df: pd.DataFrame) -> pd.DataFrame:
    """Extract country breakdown from Hoppr data."""
    if df.empty:
        return df

    # Find the header row
    header_row = None
    for idx, row in df.iterrows():
        vals = [str(v).strip() for v in row.values]
        if "COUNTRY_CODE" in vals:
            header_row = idx
            break

    if header_row is None:
        return pd.DataFrame()

    headers = [str(v).strip() for v in df.iloc[header_row].values]
    data_df = df.iloc[header_row + 1:].copy()

    # Find country columns (second DATE occurrence onwards)
    country_col_names = ["COUNTRY_CODE", "TOTAL_NO_OF_QUERIES", "TOTAL_UNIQUE_USER_EMAILS",
                         "TOTAL_UNIQUE_SELLERS", "NEW_SIGNUPS", "LOGGED_IN_SELLER",
                         "SELLERS_WITH_CONNECTED_CHANNELS"]

    # Find the second DATE (for country table)
    date_positions = [i for i, h in enumerate(headers) if h == "DATE"]
    if len(date_positions) < 2:
        return pd.DataFrame()

    country_date_idx = date_positions[1]
    country_code_idx = headers.index("COUNTRY_CODE")

    country_indices = [country_date_idx, country_code_idx]
    for name in country_col_names[1:]:
        # Find this column AFTER the country_code position
        for i in range(country_code_idx + 1, len(headers)):
            if headers[i] == name:
                country_indices.append(i)
                break

    result = data_df.iloc[:, country_indices].copy()
    col_labels = ["date", "country", "total_queries", "unique_users",
                  "unique_sellers", "new_signups", "logged_in", "connected"]
    result.columns = col_labels[:len(country_indices)]

    result["date"] = result["date"].astype(str).str.strip()
    result = result[result["date"] != ""].copy()
    result = result[result["date"] != "nan"].copy()
    result["date"] = pd.to_datetime(result["date"], errors="coerce")
    result = result.dropna(subset=["date"])

    for col in result.columns[2:]:
        result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0).astype(int)

    return result.sort_values("date").reset_index(drop=True)


def compute_hoppr_wow(daily: pd.DataFrame) -> pd.DataFrame:
    """Compute week-over-week changes for Hoppr metrics."""
    if daily.empty:
        return daily

    daily = daily.copy()
    daily["week"] = daily["date"].dt.isocalendar().week.astype(int)
    daily["year"] = daily["date"].dt.year

    weekly = daily.groupby(["year", "week"]).agg({
        "total_queries": "sum",
        "unique_users": "sum",
        "unique_sellers": "sum",
        "new_signups": "sum",
    }).reset_index()

    for col in ["total_queries", "unique_users", "unique_sellers", "new_signups"]:
        weekly[f"{col}_wow"] = weekly[col].pct_change() * 100

    return weekly


# ── Turbo Processing ─────────────────────────────────────────────────────────

def process_turbo_health(df: pd.DataFrame) -> pd.DataFrame:
    """Process Turbo usage health score data."""
    if df.empty:
        return df

    cols = df.columns.tolist()

    # First 3 columns: ACCOUNT, DISPLAY_NAME, COUNTRY_CODE
    # Remaining columns: weekly scores (dates like "9 Mar", "2 Mar", "2025-07-14")
    week_cols = cols[3:]

    result = df.copy()
    # Rename first 3 columns to standard names
    rename_map = {cols[0]: "account_id", cols[1]: "display_name", cols[2]: "country"}
    result = result.rename(columns=rename_map)

    # Clean week column names — strip whitespace
    clean_week_names = []
    for wc in week_cols:
        name = str(wc).strip()
        # Skip truly unnamed columns
        if name.startswith("Unnamed"):
            continue
        clean_week_names.append((wc, name))

    # Keep only valid week columns
    valid_week_originals = [wc for wc, _ in clean_week_names]
    valid_week_labels = [name for _, name in clean_week_names]

    result = result[["account_id", "display_name", "country"] + valid_week_originals].copy()
    result.columns = ["account_id", "display_name", "country"] + valid_week_labels

    # Filter out empty rows and the header echo row
    result["account_id"] = result["account_id"].astype(str)
    result = result[result["account_id"].str.strip() != ""].copy()
    result = result[result["account_id"] != "ACCOUNT"].copy()
    result = result[result["account_id"] != "nan"].copy()

    # Convert scores to numeric
    for col in valid_week_labels:
        result[col] = pd.to_numeric(result[col], errors="coerce").fillna(0).astype(int)

    return result


def compute_turbo_trends(health_df: pd.DataFrame) -> pd.DataFrame:
    """Compute trend indicators for each account."""
    if health_df.empty:
        return pd.DataFrame()

    week_cols = [c for c in health_df.columns if c not in ("account_id", "display_name", "country")]

    records = []
    for _, row in health_df.iterrows():
        scores = [row[c] for c in week_cols[:4]]  # Last 4 weeks
        current = scores[0] if scores else 0
        prev = scores[1] if len(scores) > 1 else current

        change = current - prev
        if change > 10:
            trend = "improving"
        elif change < -10:
            trend = "declining"
        else:
            trend = "stable"

        # Check if at-risk (below 30 for 3+ weeks)
        recent_3 = scores[:3]
        at_risk = all(s < 30 for s in recent_3) if len(recent_3) == 3 else False

        records.append({
            "account_id": row["account_id"],
            "display_name": row["display_name"],
            "country": row["country"],
            "current_score": current,
            "prev_score": prev,
            "change": change,
            "trend": trend,
            "at_risk": at_risk,
        })

    return pd.DataFrame(records)


# ── Revenue Processing ───────────────────────────────────────────────────────

def process_revenue_aop(df: pd.DataFrame) -> dict:
    """Process AOP revenue data into structured dict."""
    if df.empty:
        return {}

    result = {
        "business_units": {},
        "total_graas": {},
    }

    current_bu = None
    for _, row in df.iterrows():
        values = [str(v).strip() for v in row.values]

        # Detect business unit headers
        if values[1] in ("MP", "ABU", "EBU", "Platform"):
            current_bu = values[1]
            result["business_units"][current_bu] = {}
            continue

        if values[1] == "Total - Graas":
            current_bu = "Total"
            continue

        if current_bu and values[1] in ("GMV", "Revenue", "GP", "GP - Margin",
                                         "GMV - Monetized", "GMV - Free"):
            metric = values[1]
            data = {}

            # Parse quarterly values based on known positions
            # Actual 2024: cols 2-5, AOP 2025: cols 8-11, Actual 2025: cols 14-17
            # AOP 2026: cols 26-29, Actual 2026: cols 32-35, Achievement 2026: cols 38-41
            def parse_money(s):
                s = str(s).replace("$", "").replace(",", "").strip()
                try:
                    return float(s)
                except (ValueError, TypeError):
                    return 0.0

            def parse_pct(s):
                s = str(s).replace("%", "").strip()
                try:
                    return float(s)
                except (ValueError, TypeError):
                    return 0.0

            data["actual_2024"] = {
                "Q1": parse_money(values[2]), "Q2": parse_money(values[3]),
                "Q3": parse_money(values[4]), "Q4": parse_money(values[5]),
                "total": parse_money(values[6]) if len(values) > 6 else 0,
            }

            data["target_2026"] = {
                "Q1": parse_money(values[26]) if len(values) > 26 else 0,
                "Q2": parse_money(values[27]) if len(values) > 27 else 0,
                "Q3": parse_money(values[28]) if len(values) > 28 else 0,
                "Q4": parse_money(values[29]) if len(values) > 29 else 0,
                "total": parse_money(values[30]) if len(values) > 30 else 0,
            }

            data["actual_2026"] = {
                "Q1": parse_money(values[32]) if len(values) > 32 else 0,
                "Q2": parse_money(values[33]) if len(values) > 33 else 0,
                "Q3": parse_money(values[34]) if len(values) > 34 else 0,
                "Q4": parse_money(values[35]) if len(values) > 35 else 0,
                "total": parse_money(values[36]) if len(values) > 36 else 0,
            }

            data["achievement_2026"] = {
                "Q1": parse_pct(values[38]) if len(values) > 38 else 0,
                "Q2": parse_pct(values[39]) if len(values) > 39 else 0,
                "Q3": parse_pct(values[40]) if len(values) > 40 else 0,
                "Q4": parse_pct(values[41]) if len(values) > 41 else 0,
            }

            if current_bu == "Total":
                result["total_graas"][metric] = data
            else:
                result["business_units"][current_bu][metric] = data

    return result


def detect_anomalies(series: pd.Series, threshold: float = 2.0) -> pd.Series:
    """Flag values that are more than `threshold` std devs from the mean."""
    mean = series.mean()
    std = series.std()
    if std == 0:
        return pd.Series(False, index=series.index)
    z_scores = (series - mean).abs() / std
    return z_scores > threshold
