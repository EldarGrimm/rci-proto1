import pandas as pd
import pgeocode
import re

# Initialize Nominatim for U.S. ZIP codes
_nom = pgeocode.Nominatim('us')

def get_state_from_zip(zip_code: str):
    """
    Given a ZIP code, return [state_name, county_name].
    Returns None if ZIP is invalid or not found.
    """
    location = _nom.query_postal_code(zip_code)
    if location.empty or pd.isna(location.state_name) or pd.isna(location.county_name):
        return None
    return [location.state_name.strip(), location.county_name.strip()]

def normalize_county_name(name: str) -> str:
    """
    Normalize county names:
    - Remove 'County' or 'Parish'
    - Strip spaces
    - Uppercase for consistent matching
    """
    if not isinstance(name, str):
        return ""
    # Remove words like "County" or "Parish"
    name = re.sub(r'\b(County|Parish)\b', '', name, flags=re.IGNORECASE)
    return name.strip().upper()

def normalize_state_name(name: str) -> str:
    """
    Normalize state names:
    - Remove spaces
    - Uppercase
    """
    return str(name).strip().upper()

def get_eal_score(csv_path, county_name, state_name):
    # Load the CSV file
    df = pd.read_csv(csv_path)
    
    # Normalize dataframe columns
    df['COUNTY'] = df['COUNTY'].astype(str).apply(normalize_county_name)
    df['STATE'] = df['STATE'].astype(str).apply(normalize_state_name)
    
    # Normalize input values
    county_name = normalize_county_name(county_name)
    state_name = normalize_state_name(state_name)
    
    # Filter by both county and state
    result = df.loc[
        (df['COUNTY'] == county_name) & (df['STATE'] == state_name),
        'EAL_SCORE'
    ]
    
    if not result.empty:
        return float(result.iloc[0])
    else:
        return f"No match found for {county_name.title()} County, {state_name.title()}."

# Example usage
if __name__ == "__main__":
    csv_path = "data/NRI_Table_Counties/NRI_Table_Counties.csv"
    zip_input = input("Enter ZIP code: ").strip()
    
    location = get_state_from_zip(zip_input)
    if not location:
        print("Invalid or unknown ZIP code.")
    else:
        state_input, county_input = location
        print(f"County: {county_input}, State: {state_input}")
        score = get_eal_score(csv_path, county_input, state_input)
        print(f"EAL Score for {county_input.title()}, {state_input.title()}: {score}")
