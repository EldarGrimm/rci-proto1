import pandas as pd
import numpy as np
import pgeocode
import warnings

warnings.filterwarnings("ignore", category=pd.errors.PerformanceWarning)


# === Helper: normalize strings safely ===
def _norm(s):
    if pd.isna(s) or s is None:
        return ""
    return str(s).strip()


# === Setup Function ===
def initialize_dataset(file_path):
    """Load and preprocess Hazard Mitigation dataset."""
    df = pd.read_csv(file_path)

    # Convert date columns safely
    date_columns = ["planApprovalDate", "planExpirationDate", "apaDate", "adoptionDate"]
    for col in date_columns:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    # Sort and deduplicate
    df_sorted = df.sort_values(by="planApprovalDate", ascending=False)
    latest = df_sorted.drop_duplicates(subset=["stateAbbreviation", "placeName"], keep="first").copy()

    # Clean population
    latest["population"] = pd.to_numeric(latest["population"], errors="coerce").fillna(0)
    latest.loc[latest["population"] <= 0, "population"] = 1000

    # Log-transform
    latest["log_pop"] = np.log1p(latest["population"])

    # Global stats
    log_min = latest["log_pop"].min()
    log_max = latest["log_pop"].max()
    log_median = latest["log_pop"].median()

    # Linear score
    if log_max == log_min:
        latest["score_log_linear"] = 50.0
    else:
        latest["score_log_linear"] = ((latest["log_pop"] - log_min) / (log_max - log_min)) * 99 + 1
    latest["score_log_linear"] = latest["score_log_linear"].round(2)

    # Percentile rank
    latest["score_percentile"] = (latest["log_pop"].rank(method="average", pct=True) * 100).round(2)

    # County-level aggregation
    county_group = (
        latest.groupby(["stateAbbreviation", "countyName"], as_index=False)
        .agg(
            county_pop=("population", "sum"),
            county_score_weighted=("score_log_linear",
                lambda x: np.average(x, weights=latest.loc[x.index, "population"]))
        )
    )

    # State-level aggregation
    state_group = (
        latest.groupby("stateAbbreviation", as_index=False)
        .agg(
            state_pop=("population", "sum"),
            state_score_weighted=("score_log_linear",
                lambda x: np.average(x, weights=latest.loc[x.index, "population"]))
        )
    )

    # Build indexes
    town_index = latest.set_index(
        [latest["stateAbbreviation"].str.upper(), latest["placeName"].str.lower()]
    ).sort_index()

    county_index = county_group.set_index(
        [county_group["stateAbbreviation"].str.upper(), county_group["countyName"].str.lower()]
    )

    state_index = state_group.set_index(state_group["stateAbbreviation"].str.upper())

    return latest, town_index, county_index, state_index, log_min, log_max, log_median


# === Scoring Helper ===
def get_best_score_with_meta(state_abbrev, county_name, place_name,
                             town_index, county_index, state_index,
                             log_min, log_max, log_median):
    state_abbrev = _norm(state_abbrev).upper()
    county_name = _norm(county_name).lower()
    place_name_norm = _norm(place_name).lower()

    # Town-level
    try:
        if (state_abbrev, place_name_norm) in town_index.index:
            row = town_index.loc[(state_abbrev, place_name_norm)]
            if isinstance(row, pd.DataFrame):
                row = row.iloc[0]
            details = {
                "resolved_at": "town",
                "placeName": row.get("placeName", place_name),
                "population": int(row.get("population", 0)),
                "score_log_linear": float(row.get("score_log_linear", np.nan)),
            }
            return details["score_log_linear"], "town", details
    except Exception:
        pass

    # County-level
    try:
        if (state_abbrev, county_name) in county_index.index:
            crow = county_index.loc[(state_abbrev, county_name)]
            if isinstance(crow, pd.DataFrame):
                crow = crow.iloc[0]
            details = {
                "resolved_at": "county",
                "countyName": _norm(county_name),
                "county_score_weighted": float(crow.get("county_score_weighted", np.nan))
            }
            return details["county_score_weighted"], "county", details
    except Exception:
        pass

    # State-level
    try:
        if state_abbrev in state_index.index:
            srow = state_index.loc[state_abbrev]
            if isinstance(srow, pd.DataFrame):
                srow = srow.iloc[0]
            details = {
                "resolved_at": "state",
                "stateAbbreviation": state_abbrev,
                "state_score_weighted": float(srow.get("state_score_weighted", np.nan))
            }
            return details["state_score_weighted"], "state", details
    except Exception:
        pass

    # Global fallback
    if log_max == log_min:
        fallback = 50.0
    else:
        fallback = ((log_median - log_min) / (log_max - log_min)) * 99 + 1

    return round(fallback, 2), "global_fallback", {
        "resolved_at": "global_fallback",
        "note": "no match found for town/county/state"
    }


# === ZIP-level score function ===
def get_zip_coverage_score(zip_code):
    """Look up ZIP coverage score using global dataset indexes."""
    zip_str = str(zip_code).zfill(5)
    geo = NOMI.query_postal_code(zip_str)
    if geo is None or pd.isna(getattr(geo, "place_name", None)):
        val, lvl, meta = get_best_score_with_meta("", "", "", TOWN_INDEX, COUNTY_INDEX, STATE_INDEX, LOG_MIN, LOG_MAX, LOG_MEDIAN)
        return {"zip": zip_str, "score": val, "level": lvl, "meta": meta}

    place_name = _norm(getattr(geo, "place_name", "")).split(",")[0]
    county_name = _norm(getattr(geo, "county_name", "")).lower()
    state_abbrev = _norm(getattr(geo, "state_code", "")).upper()

    score, level, details = get_best_score_with_meta(
        state_abbrev, county_name, place_name,
        TOWN_INDEX, COUNTY_INDEX, STATE_INDEX,
        LOG_MIN, LOG_MAX, LOG_MEDIAN
    )

    return {
        "zip": zip_str,
        "place_name": place_name,
        "county_name": county_name,
        "state": state_abbrev,
        "score": round(float(score), 2),
        "level": level,
        "meta": details
    }


# === Global Variables (populated externally) ===
TOWN_INDEX = None
COUNTY_INDEX = None
STATE_INDEX = None
LOG_MIN = None
LOG_MAX = None
LOG_MEDIAN = None
NOMI = pgeocode.Nominatim("us")
