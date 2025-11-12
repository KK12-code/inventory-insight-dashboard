"""Insight helpers that sit on top of the cleaned inventory dataset."""

from __future__ import annotations

import pandas as pd

from data_loader import load_inventory_data


def low_stock_profitable(
    df: pd.DataFrame, quantity_threshold: int = 60, margin_threshold: float = 20.0
) -> pd.DataFrame:
    """Flag items that are both profitable and getting close to empty shelves."""

    # using this filter to catch high-margin items that might go out of stock soon
    mask = (df["Available_Quantity"] <= quantity_threshold) & (
        df["ProfitMargin"] >= margin_threshold
    )
    insights = (
        df.loc[mask, ["Product_ID", "Product_Name", "Available_Quantity", "Profit", "ProfitMargin"]]
        .sort_values(by=["ProfitMargin", "Profit"], ascending=False)
        .reset_index(drop=True)
    )

    print(
        f"[low_stock_profitable] {insights.shape[0]} items match "
        f"(qty <= {quantity_threshold}, margin >= {margin_threshold}%)"
    )
    if not insights.empty:
        print(
            f"  Quick tip: top candidate {insights.iloc[0]['Product_Name']} "
            f"shows {insights.iloc[0]['ProfitMargin']:.1f}% margin with only "
            f"{insights.iloc[0]['Available_Quantity']} units left."
        )

    return insights


def overstock_low_profit(
    df: pd.DataFrame, quantity_threshold: int = 200, margin_threshold: float = 10.0
) -> pd.DataFrame:
    """Surface items eating up shelf space without delivering returns."""

    # huge pile of inventory + weak margin usually means promo or bundle opportunity
    mask = (df["Available_Quantity"] >= quantity_threshold) & (
        df["ProfitMargin"] <= margin_threshold
    )
    insights = (
        df.loc[
            mask,
            [
                "Product_ID",
                "Product_Name",
                "Product_Brand",
                "Available_Quantity",
                "ProfitMargin",
                "StockValue",
            ],
        ]
        .sort_values(by=["Available_Quantity", "ProfitMargin"], ascending=[False, True])
        .reset_index(drop=True)
    )

    print(
        f"[overstock_low_profit] {insights.shape[0]} items look overstocked "
        f"(qty >= {quantity_threshold}, margin <= {margin_threshold}%)"
    )
    if not insights.empty:
        stuck_value = insights["StockValue"].sum()
        print(f"  Inventory tied up in these slow movers: ${stuck_value:,.2f}")

    return insights


def fast_moving_products(
    df: pd.DataFrame, velocity_threshold: float = 1.2, min_monthly_sales: int = 40
) -> pd.DataFrame:
    """Highlight products with a high sell-through velocity."""

    # velocity here is a quick ratio: units sold vs the average stock sitting in bins
    working_df = df[
        (df["Average_Stock_Level"] > 0) & (df["Monthly_Sale_Quantity"] >= min_monthly_sales)
    ].copy()
    working_df["SellThroughRate"] = working_df["Total_Sold"] / working_df["Average_Stock_Level"]

    insights = (
        working_df.loc[working_df["SellThroughRate"] >= velocity_threshold]
        .sort_values(by="SellThroughRate", ascending=False)
        .reset_index(drop=True)
    )[
        [
            "Product_ID",
            "Product_Name",
            "Monthly_Sale_Quantity",
            "Average_Stock_Level",
            "SellThroughRate",
            "ProfitMargin",
        ]
    ]

    print(
        f"[fast_moving_products] {insights.shape[0]} items beat velocity {velocity_threshold}x "
        f"with monthly sales >= {min_monthly_sales}"
    )
    if not insights.empty:
        print(
            f"  Fastest mover right now: {insights.iloc[0]['Product_Name']} "
            f"at {insights.iloc[0]['SellThroughRate']:.2f}x sell-through."
        )

    return insights


def brand_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Provide a tidy brand-level view for dashboards and quick sanity checks."""

    summary = (
        df.groupby("Product_Brand", dropna=False)
        .agg(
            TotalProfit=("Profit", "sum"),
            TotalStockValue=("StockValue", "sum"),
            AvgProfitMargin=("ProfitMargin", "mean"),
            SKUCount=("Product_ID", "nunique"),
        )
        .sort_values(by="TotalProfit", ascending=False)
        .reset_index()
    )

    print("[brand_summary] Brand roll-up ready:")
    print(
        summary.head(5).to_string(
            index=False,
            formatters={
                "TotalProfit": "{:,.2f}".format,
                "TotalStockValue": "{:,.2f}".format,
                "AvgProfitMargin": "{:.1f}".format,
            },
        )
    )

    return summary


if __name__ == "__main__":
    inventory_df = load_inventory_data()
    print("\n--- Low stock but profitable ---")
    low_stock_df = low_stock_profitable(inventory_df)
    print(low_stock_df.head(5).to_string(index=False))

    print("\n--- Overstocked low profit ---")
    overstock_df = overstock_low_profit(inventory_df)
    print(overstock_df.head(5).to_string(index=False))

    print("\n--- Fast moving products ---")
    fast_movers_df = fast_moving_products(inventory_df)
    print(fast_movers_df.head(5).to_string(index=False))

    print("\n--- Brand summary ---")
    brand_df = brand_summary(inventory_df)
    print(brand_df.head(5).to_string(index=False))
