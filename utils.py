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

def get_filtered_index(df, year, election, locality, state, party):
    dff = df[(df["year"] == year) & (df["election_folder"] == election)]
    if election == "General":
        dff = dff[dff["locality_type"] == locality]
        if locality == "State":
            dff = dff[dff["state"] == state]
    else:
        dff = dff[dff["party"] == party] if party else dff[dff["party"].isnull() | (dff["party"] == "")]
    return dff

def prepare_grouped_data(df, denom, num, orientation, weight_col,
                              hide_missing=True, hide_excluded=True):
    """
    Returns: (count_df, percent_df)
      - count_df: unweighted counts by (denom, num) + a 'Total' row (overall breakout by num)
      - percent_df: weighted percentages by (denom, num) + a 'Total' row (overall breakout by num)
    Assumes EXCLUDE_VALUES is defined in the outer scope.
    """

    # 0) Ensure weights are numeric
    if df[weight_col].dtype == object:
        df = df.copy()
        df[weight_col] = pd.to_numeric(df[weight_col], errors='coerce')

    # 1) Base grouped frames
    grouped_w = (
        df.groupby([denom, num], dropna=False)[weight_col]
          .sum()
          .reset_index()
    )
    grouped_c = (
        df.groupby([denom, num], dropna=False)
          .size()
          .reset_index(name="Count")
    )

    # 2) Percentages (weighted) — normalize within key
    key = denom if orientation == "vertical" else num
    totals = grouped_w.groupby(key, dropna=False)[weight_col].transform("sum")
    percent_df = grouped_w.copy()
    percent_df["Percentage"] = (percent_df[weight_col] / totals * 100).round(0)

    # 3) Overall breakout ("Total" row) for percentages and counts
    overall_w = (
        df.groupby(num, dropna=False)[weight_col]
          .sum()
          .reset_index()
    )
    overall_w["Percentage"] = (
        overall_w[weight_col] / overall_w[weight_col].sum() * 100
    ).round(0)

    overall_c = (
        df.groupby(num, dropna=False)
          .size()
          .reset_index(name="Count")
    )

    # If denom is categorical, safely add 'Total' as a category
    def _inject_total_category(base_df, colname):
        if pd.api.types.is_categorical_dtype(base_df[colname]):
            base_df[colname] = base_df[colname].cat.add_categories(["Total"])
        return base_df

    percent_df = _inject_total_category(percent_df, denom)
    grouped_c   = _inject_total_category(grouped_c, denom)

    # Label total rows
    overall_w[denom] = "Total"
    overall_c[denom] = "Total"

    # Align columns/order & append totals
    percent_df = percent_df.reindex(columns=[denom, num, weight_col, "Percentage"])
    overall_w  = overall_w.reindex(columns=[denom, num, weight_col, "Percentage"])
    percent_df = pd.concat([percent_df, overall_w], ignore_index=True)

    count_df = grouped_c.reindex(columns=[denom, num, "Count"])
    overall_c = overall_c.reindex(columns=[denom, num, "Count"])
    count_df = pd.concat([count_df, overall_c], ignore_index=True)

    # 4) Apply filters AFTER computation (and reindex masks to the current frame)
    # Build masks for each frame separately (avoids reindex warnings)
    def _apply_filters(frame):
        mask_excluded = frame[denom].isin(EXCLUDE_VALUES) | frame[num].isin(EXCLUDE_VALUES)
        mask_missing  = frame[denom].isna() | frame[num].isna()

        out = frame
        if hide_excluded:
            out = out[~mask_excluded.reindex(out.index, fill_value=False)]
        if hide_missing:
            out = out[~mask_missing.reindex(out.index, fill_value=False)]
        return out

    percent_df = _apply_filters(percent_df)
    count_df  = _apply_filters(count_df)

    # 5) Keep 'Total' at the bottom (if present)
    def _sort_total_last(frame):
        is_total = (frame[denom].astype(str) == "Total").astype(int)
        return (frame.assign(__is_total=is_total)
                    .sort_values("__is_total")
                    .drop(columns="__is_total")
                    .reset_index(drop=True))

    percent_df = _sort_total_last(percent_df)
    count_df   = _sort_total_last(count_df)

    return count_df, percent_df

def create_percent_charts(percent_df, denom, num, orientation):

    grouped = percent_df[percent_df[denom].astype(str) != "Total"]
    figures = []
    keys = grouped[denom].unique() if orientation == "vertical" else grouped[num].unique()
    var_col = num if orientation == "vertical" else denom

    var_values = grouped[var_col].dropna().unique()

    # === Candidate-specific color logic ===
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

    # Gray slice settings
    LEFTOVER_LABEL = "N/A"   # internal placeholder
    GRAY = "#BDBDBD"
    color_map[LEFTOVER_LABEL] = GRAY

    for key_val in keys:
        mask = grouped[denom if orientation == "vertical" else num] == key_val
        filtered = grouped.loc[mask].copy()
        if filtered.empty:
            continue

        col = var_col
        filtered = filtered.dropna(subset=[col]).copy()

        cats_order = sorted([str(v).strip() for v in var_values])
        filtered[col] = filtered[col].astype(str).str.strip()
        filtered[col] = pd.Categorical(filtered[col], categories=cats_order, ordered=True)
        filtered = filtered.sort_values(by=col)

        subtotal = float(filtered["Percentage"].sum())
        leftover = max(0.0, round(100.0 - subtotal, 0))

        if leftover > 0:
            extra = {
                (denom if orientation == "vertical" else num): key_val,
                col: LEFTOVER_LABEL,
                "Percentage": leftover,
            }
            filtered = pd.concat([filtered, pd.DataFrame([extra])], ignore_index=True)

        # Build the figure
        fig = px.pie(
            filtered,
            names=col,
            values="Percentage",
            hole=0.5,
            title=key_val,
            color=col,
            color_discrete_map=color_map,
            hover_data=[],
        )

        # Create text labels: just numbers, no names. Leftover slice blank.
        new_text = []
        for _, row in filtered.iterrows():
            if row[col] == LEFTOVER_LABEL:
                new_text.append("")   # hide gray slice text
            else:
                new_text.append(f"{int(row['Percentage'])}%")  # just percent number

        fig.update_traces(
            text=new_text,
            textinfo="text",
            hovertemplate="%{percent:.0%}<extra></extra>",
            showlegend=True,
            sort=False,
        )

        # Hide legend entry for the gray slice
        for i, trace in enumerate(fig.data):
             fig.data[i].showlegend = True

        fig.update_layout(
            legend=dict(x=1.2, y=0.5, xanchor="left", orientation="v", font=dict(size=12)),
            margin=dict(t=50, b=50, l=50, r=150),
        )

        figures.append(
            dcc.Graph(
                figure=fig, style={"display": "inline-block", "width": "32%", "height": "400px"}
            )
        )

    return html.Div(figures, style={"display": "flex", "flexWrap": "wrap", "gap": "20px"})


def format_table_data(grouped, denom, num, y_col, mode):
    grouped_wide = grouped.pivot(index=num, columns=denom, values=y_col)
    if mode == "percent":
        for col in grouped_wide.columns:
            if pd.api.types.is_numeric_dtype(grouped_wide[col]):
                grouped_wide[col] = (
                    grouped_wide[col].replace([np.inf, -np.inf], np.nan)
                                     .fillna(0).round(0).astype(int).astype(str) + "%"
                )
    columns = [{"name": str(col), "id": str(col)} for col in grouped_wide.reset_index().columns]
    data = grouped_wide.reset_index().to_dict("records")
    return grouped_wide, columns, data