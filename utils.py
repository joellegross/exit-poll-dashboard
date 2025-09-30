# utils.py
import pandas as pd
import numpy as np
import re
import json
import plotly.express as px
from dash import dcc, html
import os

EXCLUDED_COLS = {"ID", "PRECINCT", "STANUM", "BACKSIDE", "TELEPOLL", "CALL", "CDNUM", "VERSION",
                 "ZCODE1", "ZCODE2", "ZCODE3", "ZCODE4", "GEOCODE"}
EXCLUDE_VALUES = {"Did not vote", "None", "Other", None, " ", "Omit"}

# Load general presidential candidate party map
candidate_map_path = os.path.join("data", "general_presidential_candidates_party_map.json")
with open(candidate_map_path, "r") as f:
    CANDIDATE_PARTY_MAP = json.load(f)

PARTY_COLORS = {
    "Democrat": "#1f77b4",   # blue
    "Republican": "#d62728", # red
    "Other": "#7f7f7f"       # gray
}

def get_weight_column(df):
    for col in df.columns:
        if re.search(r"(WEIGHT|WGT)", col.upper()):
            return col
    return None

def get_valid_columns(df, weight_col):
    excluded = EXCLUDED_COLS.copy()
    if weight_col:
        excluded.add(weight_col)
    return [col for col in df.columns if col not in excluded and not re.search(r"_\d+", col)]

def prepare_grouped_data(df, denom, num, weight_col=None, hide_missing=True, hide_excluded=True):
    dff = df.copy()

    # Optional filters
    if hide_missing:
        dff = dff[dff[denom].notna() & dff[num].notna()]
    if hide_excluded and 'EXCLUDED_FLAG' in dff.columns:
        dff = dff[~dff['EXCLUDED_FLAG'].astype(bool)]

    # Weights
    use_weights = weight_col and weight_col in dff.columns
    if use_weights:
        dff = dff.copy()
        dff[weight_col] = pd.to_numeric(dff[weight_col], errors="coerce").fillna(0.0)

    # --- Counts
    if use_weights:
        grouped_w = (
            dff.groupby([denom, num], dropna=False)[weight_col]
               .sum()
               .reset_index()
               .rename(columns={weight_col: "WeightSum"})
        )
        count_df = grouped_w.rename(columns={"WeightSum": "Count"})
    else:
        count_df = (
            dff.groupby([denom, num], dropna=False)
               .size()
               .reset_index(name="Count")
        )

    # --- Percentages (normalize within denom)
    totals = count_df.groupby(denom, dropna=False)["Count"].transform("sum")
    percent_df = count_df.copy()
    percent_df["Percentage"] = (percent_df["Count"] / totals * 100).fillna(0)

    # --- Overall “Total” rows ---
    overall_c = (
        count_df.groupby(num, dropna=False)["Count"].sum().reset_index()
    )
    overall_c[denom] = "Total"

    overall_p = overall_c.copy()
    overall_p["Percentage"] = (
        overall_p["Count"] / overall_p["Count"].sum() * 100
    ).fillna(0)

    # Append “Total”
    count_df  = pd.concat([count_df, overall_c], ignore_index=True)
    percent_df = pd.concat([percent_df, overall_p], ignore_index=True)

    # Keep “Total” last
    def _sort_total_last(frame):
        is_total = (frame[denom].astype(str) == "Total").astype(int)
        return (frame.assign(__is_total=is_total)
                     .sort_values(["__is_total", denom, num])
                     .drop(columns="__is_total")
                     .reset_index(drop=True))

    return _sort_total_last(count_df), _sort_total_last(percent_df)

# ================== SOLO helpers =====================
def prepare_solo_data(df, var, weight_col=None, hide_missing=True, hide_excluded=True):
    """
    Returns (count_df, percent_df) for a single variable.
    Columns: [var, Count] and [var, Count, Percentage]
    """
    dff = df.copy()

    # Optional filters
    if hide_missing:
        dff = dff[dff[var].notna()]
    if hide_excluded and "EXCLUDED_FLAG" in dff.columns:
        dff = dff[~dff["EXCLUDED_FLAG"].astype(bool)]

    # Weights
    use_weights = bool(weight_col) and (weight_col in dff.columns)
    if use_weights:
        dff = dff.copy()
        dff[weight_col] = pd.to_numeric(dff[weight_col], errors="coerce").fillna(0.0)

        count_df = (
            dff.groupby(var, dropna=False)[weight_col]
              .sum()
              .reset_index()
              .rename(columns={weight_col: "Count"})
        )
    else:
        count_df = (
            dff.groupby(var, dropna=False)
              .size()
              .reset_index(name="Count")
        )

    total = float(count_df["Count"].sum())
    percent_df = count_df.copy()
    percent_df["Percentage"] = (percent_df["Count"] / total * 100.0).fillna(0.0).round(2) if total else 0.0

    # Keep categories sorted (string-safe)
    def _safe_key(x): return str(x)
    count_df    = count_df.sort_values(by=var, key=lambda s: s.map(_safe_key)).reset_index(drop=True)
    percent_df  = percent_df.sort_values(by=var, key=lambda s: s.map(_safe_key)).reset_index(drop=True)
    return count_df, percent_df

def create_solo_chart(percent_df, var):
    """
    Donut pie for a single variable distribution.
    """
    if percent_df.empty:
        return html.Div()

    # Handle candidate-specific coloring if applicable
    var_values = percent_df[var].dropna().unique()
    normalized_party_lookup = {name.lower().strip(): party for name, party in CANDIDATE_PARTY_MAP.items()}
    num_matches = sum(
        1 for v in var_values if isinstance(v, str) and v.lower().strip() in normalized_party_lookup
    )
    is_pres_candidate_question = num_matches >= max(1, len(var_values) / 2)

    if is_pres_candidate_question:
        color_map = {}
        for name in var_values:
            norm_name = name.lower().strip() if isinstance(name, str) else str(name).lower().strip()
            party = normalized_party_lookup.get(norm_name, "Other")
            color_map[name] = PARTY_COLORS.get(party, PARTY_COLORS["Other"])
    else:
        default_colors = px.colors.qualitative.Set3 + px.colors.qualitative.Set1
        color_map = {
            cat: default_colors[i % len(default_colors)]
            for i, cat in enumerate(sorted(var_values, key=lambda x: str(x)))
        }

    fig = px.pie(
        percent_df,
        names=var,
        values="Percentage",
        hole=0.5,
        color=var,
        color_discrete_map=color_map,
    )

    fig.update_traces(
        text=[f"{int(v)}%" for v in percent_df["Percentage"]],
        textinfo="text",
        hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
        sort=False,
    )

    fig.update_layout(
        margin=dict(t=50, b=50, l=50, r=50),
        showlegend=True
    )

    return dcc.Graph(figure=fig)

def format_table_data(grouped, denom, num, y_col, mode):
    grouped_wide = (
        grouped
        .pivot_table(index=num, columns=denom, values=y_col, aggfunc="sum")
    )

    grouped_wide = grouped_wide.apply(pd.to_numeric, errors="coerce") \
                               .replace([np.inf, -np.inf], np.nan)

    if mode == "percent":
        grouped_wide = grouped_wide.fillna(0).round(0).astype("Int64")
        grouped_wide = grouped_wide.astype(str) + "%"
    else:
        grouped_wide = grouped_wide.fillna(0).round(0).astype("Int64")

    df_out = grouped_wide.reset_index()
    df_out = df_out.where(pd.notna(df_out), None)
    if "Omit" in df_out:
        df_out.drop('Omit', axis=1, inplace=True)

    other_columns = [col for col in df_out.columns if col != "Total"]
    new_column_order = other_columns + ["Total"] if "Total" in df_out.columns else other_columns
    df_out = df_out[new_column_order]

    columns = [{"name": str(c), "id": str(c)} for c in df_out.columns]
    data = df_out.to_dict("records")

    return grouped_wide, columns, data

def format_solo_table(grouped: pd.DataFrame, var: str, y_col: str, mode: str):
    """
    Table for solo variable: [var, Count] or [var, Percentage]
    """
    if grouped.empty or var not in grouped.columns or y_col not in grouped.columns:
        return [], []

    df_out = grouped[[var, y_col]].copy()
    df_out[var] = df_out[var].astype(str)

    if mode == "percent":
        df_out[y_col] = (
            pd.to_numeric(df_out[y_col], errors="coerce")
              .fillna(0)
              .round(0)
              .astype(int)
              .astype(str) + "%"
        )
    else:
        df_out[y_col] = (
            pd.to_numeric(df_out[y_col], errors="coerce")
              .fillna(0)
              .round(0)
              .astype("Int64")
        )

    df_out = df_out.where(pd.notna(df_out), None)
    columns = [{"name": str(c), "id": str(c)} for c in df_out.columns]
    data = df_out.to_dict("records")
    return columns, data

def create_percent_charts(percent_df, denom, num):
    """
    Create donut pie charts for each category of denom, showing distribution of num.
    """
    if denom is None or num is None or percent_df.empty:
        return html.Div()

    # Drop any total-row from denom
    grouped = percent_df[percent_df[denom].astype(str) != "Total"].copy()
    figures = []

    # Keys: one chart per denom value
    keys = grouped[denom].dropna().unique()
    var_col = num  # categories live here

    # Unique categories across whole dataset (for consistent color mapping/order)
    var_values = grouped[var_col].dropna().unique()

    # Candidate-specific color logic
    normalized_party_lookup = {name.lower().strip(): party for name, party in CANDIDATE_PARTY_MAP.items()}
    num_matches = sum(
        1 for v in var_values if isinstance(v, str) and v.lower().strip() in normalized_party_lookup
    )
    is_pres_candidate_question = num_matches >= max(1, len(var_values) / 2)

    if is_pres_candidate_question:
        color_map = {}
        for name in var_values:
            norm_name = name.lower().strip() if isinstance(name, str) else str(name).lower().strip()
            party = normalized_party_lookup.get(norm_name, "Other")
            color_map[name] = PARTY_COLORS.get(party, PARTY_COLORS["Other"])
    else:
        default_colors = px.colors.qualitative.Set3 + px.colors.qualitative.Set1
        color_map = {
            cat: default_colors[i % len(default_colors)]
            for i, cat in enumerate(sorted(var_values, key=lambda x: str(x)))
        }

    for key_val in keys:
        filtered = grouped.loc[grouped[denom] == key_val].copy()
        if filtered.empty:
            continue

        subtotal = float(filtered["Percentage"].sum())
        leftover = max(0.0, round(100.0 - subtotal, 0))
        if leftover > 0:
            extra = {denom: key_val, var_col: "N/A", "Percentage": leftover}
            filtered = pd.concat([filtered, pd.DataFrame([extra])], ignore_index=True)

        fig = px.pie(
            filtered,
            names=var_col,
            values="Percentage",
            hole=0.5,
            title=str(key_val),
            color=var_col,
            color_discrete_map=color_map,
        )

        fig.update_traces(
            text=[f"{int(v)}%" if v > 0 else "" for v in filtered["Percentage"]],
            textinfo="text",
            hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            sort=False,
        )

        fig.update_layout(
            legend=dict(x=1.2, y=0.5, xanchor="left", orientation="v", font=dict(size=12)),
            margin=dict(t=50, b=50, l=50, r=150),
        )

        figures.append(
            dcc.Graph(figure=fig, style={"display": "inline-block", "width": "32%", "height": "400px"})
        )

    return html.Div(figures, style={"display": "flex", "flexWrap": "wrap", "gap": "20px"})