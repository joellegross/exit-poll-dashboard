# callbacks.py
from dash import Input, Output, State, dcc, html, dash_table
import pandas as pd
import os

import json

DATA_ROOT = os.path.join(os.path.dirname(__file__), "data")

variable_metadata_path = os.path.join("data", "master_variable_index_enhanced.json")
with open(variable_metadata_path, "r", encoding="utf-8") as f:
    VARIABLE_METADATA = json.load(f)

from utils import (
    EXCLUDE_VALUES,
    get_weight_column,
    get_valid_columns,
    get_filtered_index,
    prepare_grouped_data,
    create_percent_charts,
    format_table_data,
    create_solo_chart,
    prepare_solo_data,
    format_solo_table,
    apply_multiple_filters
)

def register_callbacks(app, df_path):
    df = pd.read_csv(df_path)
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


    @app.callback(
        Output("var1-dropdown", "options"),
        Output("var1-dropdown", "value"),
        Output("var2-dropdown", "options"),
        Output("var2-dropdown", "value"),
        Input("year-dropdown", "value"),
        Input("election-dropdown", "value"),
        Input("state-dropdown", "value"),
        Input("locality-dropdown", "value"),
        Input("party-dropdown", "value"),
        State("var1-dropdown", "value"),
        State("var2-dropdown", "value"),
    )
    def setup_var_dropdowns(year, election, state, locality, party, var1_curr, var2_curr):
        dff = get_filtered_index(df, year, election, locality, state, party)
        if dff.empty:
            return [], None, [], None

        filepath = os.path.join(DATA_ROOT, dff.iloc[0]["path"])
        df_file = pd.read_csv(filepath, low_memory=False)
        df_file.columns = [c.upper().strip() for c in df_file.columns]

        weight_col = get_weight_column(df_file)
        valid_cols = get_valid_columns(df_file, weight_col)
        opts = sorted([{"label": c, "value": c} for c in valid_cols], key=lambda x: x["label"])

        var1_val = var1_curr if var1_curr in valid_cols else None
        var2_val = var2_curr if (var2_curr in valid_cols and var2_curr != var1_val) else None

        return opts, var1_val, opts, var2_val

    @app.callback(
        Output("condition-container", "style"),
        Input("var1-dropdown", "value"),
    )
    def toggle_condition(var1):
        if var1:
            return {"display": "block", "marginTop": "10px"}
        return {"display": "none"}

    @app.callback(
        Output("filter-var-dropdown", "options"),
        Input("year-dropdown", "value"),
        Input("election-dropdown", "value"),
        Input("state-dropdown", "value"),
        Input("locality-dropdown", "value"),
        Input("party-dropdown", "value"),
        State("filter-var-dropdown", "value"),
    )
    def setup_filter_var(year, election, state, locality, party, current):

        dff = get_filtered_index(df, year, election, locality, state, party)
        if dff.empty:
            return []

        filepath = os.path.join(DATA_ROOT, dff.iloc[0]["path"])
        df_file = pd.read_csv(filepath, low_memory=False)
        df_file.columns = [c.upper().strip() for c in df_file.columns]

        weight_col = get_weight_column(df_file)
        valid_cols = get_valid_columns(df_file, weight_col)

        options = sorted([str(v) for v in valid_cols])

        return options

    @app.callback(
        Output("filter-value-dropdown", "options"),
        Input("filter-var-dropdown", "value"),
        Input("year-dropdown", "value"),
        Input("election-dropdown", "value"),
        Input("state-dropdown", "value"),
        Input("locality-dropdown", "value"),
        Input("party-dropdown", "value"),
        State("filter-value-dropdown", "value"),
        prevent_initial_call=True
    )
    def setup_filter_value(filter_var, year, election, state, locality, party, current_value):

        if not filter_var:
            return []

        dff = get_filtered_index(df, year, election, locality, state, party)
        if dff.empty:
            return []

        filepath = os.path.join(DATA_ROOT, dff.iloc[0]["path"])
        df_file = pd.read_csv(filepath, low_memory=False)
        df_file.columns = [c.upper().strip() for c in df_file.columns]

        values = df_file[filter_var].dropna().unique()
        values = [v for v in values if v not in EXCLUDE_VALUES]

        return values

    @app.callback(
        Output("filters-store", "data"),
        Input("filter-var-dropdown", "value"),
        Input("filter-value-dropdown", "value"),
        State("filters-store", "data"),
    )
    def save_filter(var, val, store):
        store = store or {}
        if var is None:
            return {}
        if val is None:
            store.pop(var, None)
            return store
        store[var] = val
        return store

    @app.callback(
        Output("denominator-choice-container", "style"),
        Output("denom-choice", "options"),
        Output("denom-choice", "value"),
        Input("var1-dropdown", "value"),
        Input("var2-dropdown", "value"),
        State("denom-choice", "value"),
    )
    def toggle_denominator_question(var1, var2, current_choice):
        if not var1 or not var2:
            return {"display": "none"}, [], None
        options = [
            {"label": f"{var1}", "value": "var1_den"},
            {"label": f"{var2}", "value": "var2_den"},
        ]
        value = current_choice if current_choice in ("var1_den", "var2_den") else "var1_den"
        return {"display": "block"}, options, value

    @app.callback(
        Output("agg-container", "style"),
        Input("var1-dropdown", "value"),
        Input("var2-dropdown", "value"),
    )
    def toggle_agg(var1, var2):
        two_vars = bool(var1) and bool(var2) and (var1 != var2)
        one_var = (bool(var1) ^ bool(var2))  # exactly one selected
        show = one_var or two_vars
        return {"display": "block"} if show else {"display": "none"}

    @app.callback(
        Output("groupby-output", "children"),
        Output("groupby-table", "columns"),
        Output("groupby-table", "data"),
        Output("sample-size-container", "children"),
        Input("year-dropdown", "value"),
        Input("election-dropdown", "value"),
        Input("state-dropdown", "value"),
        Input("locality-dropdown", "value"),
        Input("party-dropdown", "value"),
        Input("agg-mode", "value"),  # "count" | "percent"
        Input("denom-choice", "value"),
        Input("var1-dropdown", "value"),
        Input("var2-dropdown", "value"),
        Input("filters-store", "data"),
    )

    def render_outputs(year, election, state, locality, party, mode, denom_choice,
                       var1, var2, filters):
        filters_list = [
            {"var": k, "value": v}
            for k, v in (filters or {}).items()
            if k and v is not None
        ]

        # --- Which mode are we in? ---
        two_vars = bool(var1) and bool(var2) and (var1 != var2)
        one_var = (bool(var1) ^ bool(var2))
        solo_var = var1 if (var1 and not var2) else (var2 if (var2 and not var1) else None)

        # --- Load file ---
        dff = get_filtered_index(df, year, election, locality, state, party)
        if dff.empty:
            return html.P("No matching file."), [], [], ""

        filepath = os.path.join(DATA_ROOT, dff.iloc[0]["path"])
        df_file = pd.read_csv(filepath, low_memory=False)
        df_file.columns = [c.upper().strip() for c in df_file.columns]

        # --- Apply multiple filters ---
        df_file = apply_multiple_filters(df_file, filters_list)

        weight_col = get_weight_column(df_file)

        # === SOLO VARIABLE ===
        if one_var and solo_var:
            count_df, percent_df = prepare_solo_data(df_file, solo_var, weight_col, True, True)
            grouped = percent_df if mode == "percent" else count_df
            y_col = "Percentage" if mode == "percent" else "Count"

            if grouped.empty:
                return html.P("No respondents answered both selected questions.", style={"color": "red"}), [], [], ""

            chart_output = create_solo_chart(percent_df, solo_var, filters=filters)
            columns, data = format_solo_table(grouped, solo_var, y_col, mode)

            solo_q = VARIABLE_METADATA.get(solo_var, {}).get("question", "")
            sample_size = int(df_file[solo_var].notna().sum())
            sample_size_text = f"Sample size (non-missing): {sample_size:,}" if sample_size else ""

            heading = html.Div([
                html.Div(f"{solo_q}", style={"fontSize": "22px", "fontWeight": "bold", "marginBottom": "5px"})
            ])

            return html.Div([heading, chart_output]), columns, data, sample_size_text

        # === TWO VARIABLES ===
        if two_vars:
            if denom_choice == "var1_den":
                denom, num = var1, var2
            elif denom_choice == "var2_den":
                denom, num = var2, var1
            else:
                denom = num = None

            if not (denom and num and denom != num):
                return [], [], [], []

            count_df, percent_df = prepare_grouped_data(df_file, denom, num, weight_col, True, True)
            grouped = percent_df if mode == "percent" else count_df
            y_col = "Percentage" if mode == "percent" else "Count"

            if grouped.empty:
                return html.P("No respondents answered both selected questions.", style={"color": "red"}), [], [], ""

            chart_output = create_percent_charts(percent_df, denom, num, filters)
            _, columns, data = format_table_data(grouped, denom, num, y_col, mode)

            denom_q = VARIABLE_METADATA.get(denom, {}).get("question", "")
            num_q = VARIABLE_METADATA.get(num, {}).get("question", "")

            sample_df = df_file[df_file[denom].notna() & df_file[num].notna()]
            sample_size = len(sample_df)
            sample_size_text = f"Sample size: {sample_size:,}" if sample_size else ""

            question_heading = html.Div([
                html.Div(f"{denom_q}", style={"fontSize": "22px", "fontWeight": "bold",
                                              "marginBottom": "5px"}) if denom_q else html.Div(),
                html.Div(f"Broken down by: {num_q}", style={"fontSize": "22px", "fontWeight": "bold",
                                                            "marginBottom": "5px"}) if num_q else html.Div()
            ])

            return html.Div([question_heading, chart_output]), columns, data, sample_size_text

        # === Nothing selected ===
        return [], [], [], []