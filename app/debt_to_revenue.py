import pandas as pd

class DebtRevenueAnalyzer:
    def __init__(self, csv_path):
        # Load CSV
        self.df = pd.read_csv(csv_path)

        # Clean numbers in Amount column (remove commas, normalize minus signs, convert to float)
        self.df["Amount (AMOUNT)"] = (
            self.df["Amount (AMOUNT)"]
            .astype(str)
            .str.replace(",", "", regex=False)       # remove commas
            .str.replace("−", "-", regex=False)      # replace Unicode minus with ASCII minus
            .str.strip()                             # remove whitespace
            .replace("", "0")                        # blanks → 0
            .astype(float)
        )

        # Build { state: { label: amount } }
        self.state_data = {}
        for state, group in self.df.groupby("Geographic Area Name (NAME)"):
            mapping = dict(
                zip(group["Meaning of Aggregate Description (AGG_DESC_LABEL)"],
                    group["Amount (AMOUNT)"])
            )
            self.state_data[state] = mapping

        # Precompute ratios for all states
        self.all_ratios = self._compute_all_ratios()

    def _compute_all_ratios(self, 
                            debt_key="Debt - Total Debt Outstanding", 
                            revenue_key="Revenue - Total Revenue"):
        ratios = {}
        for state in self.state_data:
            ratio, _, _ = self.get_debt_to_revenue_ratio(state, debt_key, revenue_key)
            if ratio is not None:
                ratios[state] = ratio
        return ratios

    def list_categories(self, state_name):
        """List all available categories for a state."""
        return list(self.state_data.get(state_name, {}).keys())

    def get_value(self, state_name, category):
        """Fetch a specific category value for a state."""
        return self.state_data.get(state_name, {}).get(category, None)

    def get_debt_to_revenue_ratio(self, state_name,
                                  debt_key="Debt - Total Debt Outstanding",
                                  revenue_key="Revenue - Total Revenue"):
        """Calculate debt/revenue ratio for a state."""
        state_info = self.state_data.get(state_name, {})
        debt = state_info.get(debt_key)
        revenue = state_info.get(revenue_key)

        if debt is None or revenue is None or revenue == 0:
            return None, debt, revenue
        return debt / revenue, debt, revenue

    def get_relative_score(self, state_name):
        """Return 0-100 score relative to min/max ratio across all states."""
        if state_name not in self.all_ratios:
            return None

        min_r = min(self.all_ratios.values())
        max_r = max(self.all_ratios.values())
        state_r = self.all_ratios[state_name]

        if max_r == min_r:  # avoid divide by zero
            return 50  

        return ((state_r - min_r) / (max_r - min_r)) * 100


# ---------------------- Example Usage ----------------------

if __name__ == "__main__":
    analyzer = DebtRevenueAnalyzer("data/gov_revenue_metrics.csv")

    states_to_check = ["Florida", "Michigan", "Texas"]

    print("Debt-to-Revenue Ratios (with relative scores):\n")
    for st in states_to_check:
        ratio, debt, revenue = analyzer.get_debt_to_revenue_ratio(st)
        score = analyzer.get_relative_score(st)
        if ratio is not None:
            print(f"{st}:")
            print(f"  Debt    = {debt:,.0f}")
            print(f"  Revenue = {revenue:,.0f}")
            print(f"  Ratio   = {ratio:.2f}")
            print(f"  Relative Score (0–100) = {score:.1f}\n")
        else:
            print(f"{st}: Data missing (Debt={debt}, Revenue={revenue})\n")

    # Interactive query
    user_state = input("Enter a state to query (or press Enter to skip): ").strip()
    if user_state:
        ratio, debt, revenue = analyzer.get_debt_to_revenue_ratio(user_state)
        score = analyzer.get_relative_score(user_state)
        if ratio is not None:
            print(f"\n{user_state}:")
            print(f"  Debt    = {debt:,.0f}")
            print(f"  Revenue = {revenue:,.0f}")
            print(f"  Ratio   = {ratio:.2f}")
            print(f"  Relative Score (0–100) = {score:.1f}")
        else:
            print(f"\n{user_state}: Data missing (Debt={debt}, Revenue={revenue})")
