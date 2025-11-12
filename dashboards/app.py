"""Dash app that wraps the inventory insight helpers with quick visuals."""

# Keeping imports in one place so future refactors (like FastAPI backend) are painless.
from pathlib import Path

import dash
from dash import Dash, Input, Output, callback_context, dash_table, dcc, html
import pandas as pd
import plotly.express as px

# Adding src to sys.path so we can reuse the data logic without turning this into a package yet.
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from src.data_loader import load_inventory_data  # noqa: E402
from src.insights import (  # noqa: E402
    brand_summary,
    fast_moving_products,
    low_stock_profitable,
    overstock_low_profit,
)

# Load the inventory once; if we ever add live updates we can revisit this.
INVENTORY_DF = load_inventory_data()

# Mapping view keys to the functions so the callback stays tidy.
VIEW_FUNCTIONS = {
    "low-stock": low_stock_profitable,
    "over-stock": overstock_low_profit,
    "fast-moving": fast_moving_products,
    "brand-summary": brand_summary,
}

# Button metadata keeps layout + callback in sync.
VIEW_BUTTONS = [
    ("low-stock", "Low-Stock Profitable"),
    ("over-stock", "Over-Stocked Low-Profit"),
    ("fast-moving", "Fast-Moving"),
    ("brand-summary", "Brand Summary"),
]


def build_table(df: pd.DataFrame) -> dash_table.DataTable:
    """Wrap dataframe into a Dash table; future tweak could add virtualization."""

    return dash_table.DataTable(
        columns=[{"name": col, "id": col} for col in df.columns],
        data=df.to_dict("records"),
        page_size=10,
        style_table={"overflowX": "auto"},
        style_cell={"textAlign": "left", "padding": "8px"},
    )


def build_chart(view_key: str, df: pd.DataFrame):
    """Return the right Plotly figure for the selected insight."""

    if view_key == "brand-summary":
        # using Plotly Express for quick visuals here
        fig = px.pie(
            df,
            names="Product_Brand",
            values="TotalStockValue",
            title="Inventory Value by Brand",
            hole=0.35,
        )
    else:
        # Might switch to dropdown later if we add more filters or axes.
        fig = px.bar(
            df.head(15),
            x="Product_Name",
            y="Profit",
            color="ProfitMargin",
            title="Top Items by Profit",
            labels={"Profit": "Total Profit", "ProfitMargin": "Profit Margin %"},
        )
        fig.update_layout(xaxis_tickangle=-35)

    return fig


def get_insight_data(view_key: str) -> pd.DataFrame:
    """Execute the right insight function and make sure it returns a tidy slice."""

    func = VIEW_FUNCTIONS.get(view_key, low_stock_profitable)
    result_df = func(INVENTORY_DF)
    return result_df


app: Dash = dash.Dash(__name__)
app.title = "Inventory Insight Dashboard"

app.layout = html.Div(
    [
        html.Div(
            [
                html.H1("Inventory Insight Dashboard"),
                html.P("Quick peek at what's moving, what's stuck, and which brands matter."),
            ],
            className="banner",
            style={"textAlign": "center", "padding": "20px"},
        ),
        html.Div(
            [
                html.Div(
                    [
                        html.Button(label, id=f"btn-{key}", n_clicks=0, className="view-btn")
                        for key, label in VIEW_BUTTONS
                    ],
                    style={"display": "flex", "gap": "12px", "justifyContent": "center"},
                ),
            ],
            style={"marginBottom": "20px"},
        ),
        dcc.Store(id="current-view", data="low-stock"),
        html.Div(
            [
                html.Div(id="table-container", style={"marginBottom": "30px"}),
                dcc.Graph(id="insight-chart"),
            ],
            style={"padding": "0 20px"},
        ),
    ]
)


@app.callback(
    Output("current-view", "data"),
    [Input(f"btn-{key}", "n_clicks") for key, _ in VIEW_BUTTONS],
)
def update_view_store(*n_clicks):
    """Figure out which button fired and update the stored view key."""

    triggered = callback_context.triggered
    if triggered:
        button_id = triggered[0]["prop_id"].split(".")[0]
        return button_id.replace("btn-", "")
    return dash.no_update


@app.callback(
    [Output("table-container", "children"), Output("insight-chart", "figure")],
    Input("current-view", "data"),
)
def render_view(current_view: str):
    """Render table + chart whenever the user hops between insight buttons."""

    df = get_insight_data(current_view)
    table_component = build_table(df.head(20))
    chart = build_chart(current_view, df)
    return table_component, chart


if __name__ == "__main__":
    # Keeping dev server simple; can add gunicorn entrypoint later.
    app.run_server(debug=True, host="0.0.0.0", port=8050)
