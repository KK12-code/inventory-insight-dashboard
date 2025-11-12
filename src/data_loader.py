"""Inventory data ingestion and quick sanity summaries."""

from pathlib import Path
from typing import Union

import pandas as pd

# Columns we expect to behave numerically even if the CSV stores them as strings.
NUMERIC_COLUMNS = [
    "Available_Quantity",
    "Average_Selling_Price",
    "Average_Buying_Price",
    "Total_Incoming",
    "Total_Outgoing",
    "Defective_Stock",
    "Total_Sold",
    "Monthly_Sale_Quantity",
    "Holding_Cost",
    "Average_Stock_Level",
    "Profit_Per_Unit",
    "Profit_After_HC",
]


def load_inventory_data(csv_path: Union[str, Path] = Path("data/inventory.csv")) -> pd.DataFrame:
    """Read, clean, and enrich the inventory dataset."""

    csv_path = Path(csv_path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Could not find inventory file at {csv_path.resolve()}")

    df = pd.read_csv(csv_path)

    # Trim any surprises like trailing spaces so joins/groupbys behave.
    string_columns = df.select_dtypes(include="object").columns
    if len(string_columns) > 0:
        df[string_columns] = df[string_columns].apply(lambda col: col.str.strip())

    # Quick check to ensure all numeric fields are clean and ready for math.
    for column in NUMERIC_COLUMNS:
        if column in df.columns:
            df[column] = pd.to_numeric(df[column], errors="coerce")

    price_diff = df["Average_Selling_Price"] - df["Average_Buying_Price"]
    df["Profit"] = price_diff * df["Total_Sold"]
    df["StockValue"] = df["Available_Quantity"] * df["Average_Buying_Price"]
    df["ProfitMargin"] = (price_diff / df["Average_Buying_Price"]) * 100

    return df


def print_profit_highlights(inventory_df: pd.DataFrame, top_n: int = 5) -> None:
    """Print quick summaries that are handy while iterating on dashboards."""

    if "Profit" not in inventory_df.columns or "StockValue" not in inventory_df.columns:
        raise ValueError("DataFrame is missing derived columns. Call load_inventory_data first.")

    top_profitable = (
        inventory_df.sort_values("Profit", ascending=False)
        .head(top_n)[["Product_ID", "Product_Name", "Profit", "ProfitMargin"]]
    )
    print(f"\nTop {top_profitable.shape[0]} products by total profit:")
    print(top_profitable.to_string(index=False, formatters={"Profit": "{:,.2f}".format}))

    brand_summary = (
        inventory_df.groupby("Product_Brand", dropna=False)["StockValue"]
        .sum()
        .sort_values(ascending=False)
    )
    print("\nTotal inventory value by brand:")
    formatted_brand_summary = brand_summary.map(lambda value: f"{value:,.2f}")
    print(formatted_brand_summary.to_string())

    total_value = inventory_df["StockValue"].sum()
    print(f"\nOverall inventory value: ${total_value:,.2f}")


if __name__ == "__main__":
    inventory_df = load_inventory_data()
    print_profit_highlights(inventory_df)
