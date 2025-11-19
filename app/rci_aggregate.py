import warnings
warnings.filterwarnings("ignore")

import pandas as pd
import numpy as np
import os

# === Imports for each metric ===
from .hazard_mitigation_draft2 import (
    initialize_dataset,
    get_zip_coverage_score,
)
from .debt_to_revenue import DebtRevenueAnalyzer
from .bridges_1 import load_bridge_data, calculate_bridge_metrics, get_county_metric
from .EAL_finder import get_eal_score, get_state_from_zip


# === Load all static datasets once ===
BASE_DIR = os.path.dirname(__file__)

DEBT_CSV = os.path.join(BASE_DIR, "data/gov_revenue_metrics.csv")
BRIDGE_XLSX = os.path.join(BASE_DIR, "data/county25/county25.xlsx")
EAL_CSV = os.path.join(BASE_DIR, "data/NRI_Table_Counties/NRI_Table_Counties.csv")
HAZARD_CSV = os.path.join(BASE_DIR, "data/HazardMitigationPlanStatuses.csv")


# === Initialize datasets ===
debt_analyzer = DebtRevenueAnalyzer(DEBT_CSV)
bridge_data = calculate_bridge_metrics(load_bridge_data(BRIDGE_XLSX))

# --- Initialize hazard mitigation dataset (external setup) ---
from .hazard_mitigation_draft2 import (
    TOWN_INDEX, COUNTY_INDEX, STATE_INDEX,
    LOG_MIN, LOG_MAX, LOG_MEDIAN, NOMI
)
latest, town_idx, county_idx, state_idx, log_min, log_max, log_median = initialize_dataset(HAZARD_CSV)

# Assign to module-level globals so get_zip_coverage_score works properly
from . import hazard_mitigation_draft2 as hazard_mod
hazard_mod.TOWN_INDEX = town_idx
hazard_mod.COUNTY_INDEX = county_idx
hazard_mod.STATE_INDEX = state_idx
hazard_mod.LOG_MIN = log_min
hazard_mod.LOG_MAX = log_max
hazard_mod.LOG_MEDIAN = log_median


# === Master RCI calculator ===
def calculate_rci(zip_code):
    """Compute combined RCI from hazard, debt, bridge, and EAL metrics."""
    loc = get_state_from_zip(zip_code)
    if not loc:
        return {"zip": zip_code, "error": "Invalid ZIP code or no match found."}
    state_name, county_name = loc

    haz_data = get_zip_coverage_score(zip_code)
    haz_score = haz_data.get("score", None)

    debt_score = debt_analyzer.get_relative_score(state_name)
    bridge_score = get_county_metric(bridge_data, county_name, state_name)
    eal_score_val = get_eal_score(EAL_CSV, county_name, state_name)
    eal_score = eal_score_val if isinstance(eal_score_val, (int, float)) else None

    scores = [s for s in [haz_score, debt_score, bridge_score, eal_score] if s is not None]
    rci = np.mean(scores) if scores else None

    return {
        "zip": zip_code,
        "state": state_name,
        "county": county_name,
        "hazard_score": haz_score,
        "debt_revenue_score": debt_score,
        "bridge_score": bridge_score,
        "eal_score": eal_score,
        "rci": round(rci, 2) if rci is not None else None
    }


# === Interactive test ===
if __name__ == "__main__":
    while True:
        zip_input = input("\nEnter ZIP code (or 'exit' to quit): ").strip()
        if zip_input.lower() == "exit":
            break
        result = calculate_rci(zip_input)
        print("\n=== RCI Results ===")
        for k, v in result.items():
            print(f"{k:20s}: {v}")
