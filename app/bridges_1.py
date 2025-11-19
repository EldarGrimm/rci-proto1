import pandas as pd
import re

def load_bridge_data(excel_path: str) -> pd.DataFrame:
    """
    Load only the 'Includes Federal Bridges' section from each sheet of the Excel workbook.
    Skips the 'Excludes Federal Bridges' section entirely.
    """
    sheets = pd.read_excel(excel_path, sheet_name=None, header=None)
    combined_data = []

    for state, df in sheets.items():
        df = df.astype(str)

        inc_idx_list = df.index[df.iloc[:, 0].str.contains("Includes Federal Bridges", case=False, na=False)].tolist()
        if not inc_idx_list:
            continue
        inc_idx = inc_idx_list[0]

        exc_idx_list = df.index[df.iloc[:, 0].str.contains("Excludes Federal Bridges", case=False, na=False)].tolist()
        exc_idx = exc_idx_list[0] if exc_idx_list else len(df)

        section = df.iloc[inc_idx:exc_idx].copy()

        start_idx_list = section.index[section.iloc[:, 0].str.contains("County", na=False, case=False)].tolist()
        if not start_idx_list:
            continue
        start_idx = start_idx_list[0]

        data = section.loc[start_idx + 1:].iloc[:, :5]
        data.columns = ["County", "All", "Good", "Fair", "Poor"]

        data = data.dropna(subset=["County"])
        data = data[~data["County"].str.contains("TOTAL", case=False, na=False)]

        data["County"] = (
            data["County"]
            .str.replace(r"\s*\(\d+\)", "", regex=True)
            .str.replace(r"county", "", case=False, regex=True)
            .str.strip()
            .str.title()
        )

        data[["All", "Good", "Fair", "Poor"]] = (
            data[["All", "Good", "Fair", "Poor"]]
            .astype(str)
            .replace({",": "", r"\s+": ""}, regex=True)
            .apply(pd.to_numeric, errors="coerce")
        )

        data["State"] = state.strip().title()
        combined_data.append(data)

    all_data = pd.concat(combined_data, ignore_index=True)
    return all_data


def calculate_bridge_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds Poor_Percentage and Relative_Metric (higher = better).
    """
    df["Poor_Percentage"] = (df["Poor"] / df["All"]) * 100
    min_val, max_val = df["Poor_Percentage"].min(), df["Poor_Percentage"].max()
    df["Relative_Metric"] = 100 * (1 - (df["Poor_Percentage"] - min_val) / (max_val - min_val))
    return df


def get_county_metric(df: pd.DataFrame, county_name: str, state_name: str = None):
    """
    Cleanly look up a county-level bridge metric by name and optional state.
    Returns the numeric Relative_Metric (0–100, higher = better) or None if no match.
    """
    if not county_name:
        return None

    county_clean = (
        str(county_name)
        .lower()
        .replace("county", "")
        .strip()
    )

    df_temp = df.copy()
    df_temp["County_Clean"] = df_temp["County"].str.lower().str.replace("county", "").str.strip()
    df_temp["State_Clean"] = df_temp["State"].str.lower().str.strip()

    # Filter by state if provided
    if state_name:
        state_clean = state_name.lower().strip()
        df_temp = df_temp[df_temp["State_Clean"].str.contains(state_clean, na=False)]

    # Exact match first
    match = df_temp[df_temp["County_Clean"] == county_clean]

    # Try partial match if exact fails
    if match.empty:
        match = df_temp[df_temp["County_Clean"].str.contains(county_clean, na=False)]

    if match.empty:
        return None

    # If multiple matches, take average (handles name duplicates across sheets)
    metric_value = match["Relative_Metric"].mean(skipna=True)
    return float(metric_value) if pd.notna(metric_value) else None


# === Manual test harness ===
if __name__ == "__main__":
    file_path = "data\\county25\\county25.xlsx"

    bridge_data = load_bridge_data(file_path)
    bridge_data = calculate_bridge_metrics(bridge_data)

    while True:
        county = input("Enter county name (or 'exit' to quit): ").strip()
        if county.lower() == "exit":
            break
        state = input("Enter state name (optional): ").strip() or None

        metric = get_county_metric(bridge_data, county, state)
        if metric is None:
            print(f"No match found for {county} ({state or 'any state'})\n")
        else:
            print(f"{county.title()} ({state or 'N/A'}): Bridge Metric = {metric:.2f}\n")
