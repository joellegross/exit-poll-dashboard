# callbacks.py
from dash import Input, Output, State, dcc, html, dash_table
import pandas as pd
import os
from utils import EXCLUDE_VALUES

import json

DATA_ROOT = os.path.join(os.path.dirname(__file__), "data")


variable_metadata_path = os.path.join("data", "master_variable_index_enhanced.json")
with open(variable_metadata_path, "r", encoding="utf-8") as f:
    VARIABLE_METADATA = json.load(f)

from utils import (
    get_weight_column,
    get_valid_columns,
    get_filtered_index,
    prepare_grouped_data,
    create_percent_charts,
    format_table_data
)

def register_callbacks(app, df_path):
    df = pd.read_csv(df_path)

    # Show party only for Primaries; show state when not National
    @app.callback(
        Output("party-container", "style"),
        Output("state-container", "style"),
        Input("election-dropdown", "value"),
        Input("locality-dropdown", "value"),
    )
    def toggle_party_and_state(election_type, locality):
        return (
            {"display": "block"} if election_type == "Primary" else {"display": "none"},
            {"display": "block"} if locality != "National" else {"display": "none"},
        )

    # Show Aggregation Type only after both columns are chosen and distinct
    @app.callback(
        Output("agg-container", "style"),
        Input("denominator-dropdown", "value"),
        Input("numerator-dropdown", "value"),
    )
    def toggle_agg(denom, num):
        show = bool(denom) and bool(num) and denom != num
        return {"display": "block"} if show else {"display": "none"}

    # Populate state options per year/election
    @app.callback(
        Output("state-dropdown", "options"),
        Output("state-dropdown", "value"),
        Input("year-dropdown", "value"),
        Input("election-dropdown", "value"),
    )
    def update_state_options(year, election):
        dff = df[(df["year"] == year) & (df["election_folder"] == election)]
        valid_states = dff["state"].dropna()
        valid_states = valid_states[~valid_states.str.upper().eq("NATIONAL")]
        options = [{"label": s, "value": s} for s in sorted(valid_states.unique())]
        return options, (options[0]["value"] if options else None)

    # Main output callback
    @app.callback(
        Output("denominator-dropdown", "options"),
        Output("denominator-dropdown", "value"),
        Output("numerator-dropdown", "options"),
        Output("numerator-dropdown", "value"),
        Output("groupby-output", "children"),
        Output("groupby-table", "columns"),
        Output("groupby-table", "data"),
        Output("sample-size-container", "children"),  # <-- new Output
        Input("year-dropdown", "value"),
        Input("election-dropdown", "value"),
        Input("state-dropdown", "value"),
        Input("locality-dropdown", "value"),
        Input("party-dropdown", "value"),
        Input("denominator-dropdown", "value"),
        Input("numerator-dropdown", "value"),
        Input("agg-mode", "value"),  # "count" | "percent"
        Input("orientation-mode", "value"),  # "horizontal" | "vertical"
    )
    def update_outputs(year, election, state, locality, party, denom, num, mode, orientation):
        try:
            dff = get_filtered_index(df, year, election, locality, state, party)
            if dff.empty:
                return [], None, [], None, html.P("No matching file."), [], [], ""

            filepath = os.path.join(DATA_ROOT, dff.iloc[0]["path"])
            df_file = pd.read_csv(filepath, low_memory=False)
            df_file.columns = [col.upper().strip() for col in df_file.columns]

            weight_col = get_weight_column(df_file)
            valid_cols = get_valid_columns(df_file, weight_col)

            options = sorted(
                [{"label": col, "value": col} for col in valid_cols],
                key=lambda x: x["label"]
            )
            denom_val = denom if denom in valid_cols else None
            num_val   = num   if (num in valid_cols and num != denom_val) else None

            if not denom_val or not num_val:
                return options, denom_val, options, num_val, html.P("Please select valid columns."), [], [], ""

            # Get both (counts & percentages), with Total-row appended and filters applied
            count_df, percent_df = prepare_grouped_data(
                df=df_file,
                denom=denom_val,
                num=num_val,
                orientation=orientation,
                weight_col=weight_col,
                hide_missing=True,
                hide_excluded=True,
            )

            # Select current view
            if mode == "percent":
                grouped = percent_df
                y_col = "Percentage"
            else:
                grouped = count_df
                y_col = "Count"

            if grouped.empty:
                return (
                    options, denom_val, options, num_val,
                    html.P("No respondents answered both selected questions.", style={"color": "red"}),
                    [], [], ""
                )

            # Charts

            chart_output = create_percent_charts(percent_df, denom_val, num_val, orientation)

            # Table
            _, columns, data = format_table_data(grouped, denom_val, num_val, y_col, mode)

            # Headings & sample size (joint non-missing)
            denom_q = VARIABLE_METADATA.get(denom_val, {}).get("question", "")
            num_q   = VARIABLE_METADATA.get(num_val, {}).get("question", "")
            q, b = (denom_q, num_q) if orientation == "vertical" else (num_q, denom_q)

            sample_df = df_file[df_file[denom_val].notna() & df_file[num_val].notna()]
            sample_size = len(sample_df)
            sample_size_text = (
                f"Sample size (non-missing): {sample_size:,}" if sample_size else ""
            )

            question_heading = html.Div([
                html.Div(f"{q}", style={"fontSize": "22px", "fontWeight": "bold", "marginBottom": "5px"}) if q else html.Div(),
                html.Div(f"Broken down by: {b}", style={"fontSize": "22px", "fontWeight": "bold", "marginBottom": "5px"}) if b else html.Div()
            ])

            return (
                options, denom_val, options, num_val,
                html.Div([question_heading, chart_output]),
                columns, data,
                sample_size_text
            )

        except Exception as e:
            return [], None, [], None, html.P(f"Error: {e}"), [], [], ""