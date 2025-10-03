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
EXCLUDE_VALUES = {
    "Did not vote", "None", "Other", "Omit",
    None, "", " ", "  ", "N/A", "NA"
}
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

def apply_multiple_filters(df, filters):

    dff = df.copy()

    if not filters:
        return dff

    for f in filters:
        var = f.get("var")
        val = f.get("value")

        if not var or val is None:
            continue

        if var not in dff.columns:
            continue

        left = dff[var].astype(str).str.strip()
        right = str(val).strip()
        dff = dff[left == right]

    return dff

def prepare_grouped_data(df, denom, num, weight_col=None, hide_missing=True, hide_excluded=True):
    dff = df.copy()

    if hide_missing:
        dff = dff[dff[denom].notna() & dff[num].notna()]
    if hide_excluded and 'EXCLUDED_FLAG' in dff.columns:
        dff = dff[~dff['EXCLUDED_FLAG'].astype(bool)]

    use_weights = weight_col and weight_col in dff.columns
    if use_weights:
        dff = dff.copy()
        dff[weight_col] = pd.to_numeric(dff[weight_col], errors="coerce").fillna(0.0)

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

    totals = count_df.groupby(denom, dropna=False)["Count"].transform("sum")
    percent_df = count_df.copy()
    percent_df["Percentage"] = (percent_df["Count"] / totals * 100).fillna(0)

    overall_c = (
        count_df.groupby(num, dropna=False)["Count"].sum().reset_index()
    )
    overall_c[denom] = "Total"

    overall_p = overall_c.copy()
    overall_p["Percentage"] = (
        overall_p["Count"] / overall_p["Count"].sum() * 100
    ).fillna(0)


    count_df  = pd.concat([count_df, overall_c], ignore_index=True)
    percent_df = pd.concat([percent_df, overall_p], ignore_index=True)

    def _sort_total_last(frame):
        is_total = (frame[denom].astype(str) == "Total").astype(int)
        return (frame.assign(__is_total=is_total)
                     .sort_values(["__is_total", denom, num])
                     .drop(columns="__is_total")
                     .reset_index(drop=True))

    return _sort_total_last(count_df), _sort_total_last(percent_df)

def prepare_solo_data(df, var, weight_col=None, hide_missing=True, hide_excluded=True):

    dff = df.copy()

    if hide_missing:
        dff = dff[dff[var].notna()]
    if hide_excluded and "EXCLUDED_FLAG" in dff.columns:
        dff = dff[~dff["EXCLUDED_FLAG"].astype(bool)]

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

    def _safe_key(x): return str(x)
    count_df    = count_df.sort_values(by=var, key=lambda s: s.map(_safe_key)).reset_index(drop=True)
    percent_df  = percent_df.sort_values(by=var, key=lambda s: s.map(_safe_key)).reset_index(drop=True)
    return count_df, percent_df

def create_solo_chart(percent_df, var, remainder_label="N/A", eps=1e-6):
    """
    Donut pie for a single variable distribution.
    - Keeps labels/tooltip equal to your df's 'Percentage' values.
    - Adds a gray remainder slice if total < 100 so areas sum to 100.
    - Collapses excluded values to 'N/A' (gray).
    """
    if percent_df.empty:
        return html.Div()

    df = percent_df.copy()

    # Excluded → "N/A"
    exclude_set = set(EXCLUDE_VALUES) | {""}
    df[var] = df[var].apply(lambda v: "N/A" if str(v).strip() in exclude_set else v)

    # Ensure numeric percentages
    df["__pct__"] = pd.to_numeric(df["Percentage"], errors="coerce").fillna(0.0)

    # Color map (candidate-aware if applicable)
    var_values = df[var].dropna().unique()
    normalized_party_lookup = {name.lower().strip(): party for name, party in CANDIDATE_PARTY_MAP.items()}
    num_matches = sum(1 for v in var_values if isinstance(v, str) and v.lower().strip() in normalized_party_lookup)
    is_pres_candidate_question = num_matches >= max(1, len(var_values) / 2)

    if is_pres_candidate_question:
        color_map = {}
        for name in var_values:
            k = name.lower().strip() if isinstance(name, str) else str(name).lower().strip()
            party = normalized_party_lookup.get(k, "Other")
            color_map[name] = PARTY_COLORS.get(party, PARTY_COLORS["Other"])
    else:
        default_colors = px.colors.qualitative.Set3 + px.colors.qualitative.Set1
        color_map = {
            cat: default_colors[i % len(default_colors)]
            for i, cat in enumerate(sorted(var_values, key=lambda x: str(x)))
        }

    # Force N/A + remainder to gray
    color_map["N/A"] = "#D3D3D3"
    color_map[remainder_label] = "#D3D3D3"

    # Add remainder wedge if needed
    total = float(df["__pct__"].sum())
    if total < 100 - eps:
        df = pd.concat(
            [df, pd.DataFrame({var: [remainder_label], "__pct__": [100.0 - total], "Percentage": [100.0 - total]})],
            ignore_index=True
        )

    # Keep a display column that mirrors your df for labels/tooltip
    df["__display__"] = df["Percentage"]

    fig = px.pie(
        df,
        names=var,
        values="__pct__",                 # areas (with possible remainder) → sum to 100
        hole=0.5,
        color=var,
        color_discrete_map=color_map,
        custom_data=["__display__"]       # your original df percentages for tooltip/labels
    )

    # Labels = df %, Tooltip = df % + normalized chart share
    fig.update_traces(
        texttemplate="%{customdata[0]:.0f}%",
        hovertemplate="%{label}: %{customdata[0]:.1f}%%"
                      "<br>share in chart: %{percent:.1%}<extra></extra>",
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

    other_columns = [col for col in df_out.columns if col != "Total"]
    new_column_order = other_columns + ["Total"] if "Total" in df_out.columns else other_columns
    df_out = df_out[new_column_order]

    columns = [{"name": str(c), "id": str(c)} for c in df_out.columns]
    data = df_out.to_dict("records")

    return grouped_wide, columns, data


def format_solo_table(grouped: pd.DataFrame, var: str, y_col: str, mode: str):

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

def _norm(v):
    return None if v is None else str(v).strip().lower()

_EXCLUDE_NORM = {_norm(v) for v in EXCLUDE_VALUES}

def _is_excluded(v):
    return _norm(v) in _EXCLUDE_NORM

def create_percent_charts(percent_df, denom, num, remainder_label="Unaccounted", eps=1e-6):
    if denom is None or num is None or percent_df.empty:
        return html.Div()

    # Drop the "Total" row and any rows whose *denominator value* is excluded
    df = percent_df[percent_df[denom].astype(str) != "Total"].copy()
    df = df[~df[denom].apply(_is_excluded)].copy()   # <-- no chart for excluded denom values

    # Make sure percentages are numeric
    df["__pct__"] = pd.to_numeric(df["Percentage"], errors="coerce").fillna(0.0)

    # Map excluded *numerator* values to "N/A" so they don't get their own colored category
    df[num] = df[num].apply(lambda v: "N/A" if _is_excluded(v) else v)

    # Colors
    default_colors = px.colors.qualitative.Set3 + px.colors.qualitative.Set1
    base_vals = [v for v in df[num].dropna().unique() if v != "N/A"]
    base_vals = sorted(base_vals, key=lambda x: str(x))
    base_color_map = {cat: default_colors[i % len(default_colors)] for i, cat in enumerate(base_vals)}
    base_color_map["N/A"] = "#D3D3D3"
    base_color_map[remainder_label] = "#D3D3D3"

    figures = []
    for key_val in df[denom].dropna().unique():
        sub = df.loc[df[denom] == key_val, [denom, num, "__pct__"]].copy()
        if sub.empty:
            continue

        total = float(sub["__pct__"].sum())
        if total < 100 - eps:
            sub = pd.concat([
                sub,
                pd.DataFrame({denom: [key_val], num: [remainder_label], "__pct__": [100.0 - total]})
            ], ignore_index=True)

        sub["__display__"] = sub["__pct__"]

        fig = px.pie(
            sub,
            names=num,
            values="__pct__",
            hole=0.5,
            title=str(key_val),
            color=num,
            color_discrete_map=base_color_map,
            custom_data=["__display__"],
        )

        fig.update_traces(
            texttemplate="%{customdata[0]:.0f}%",
            hovertemplate="%{label}: %{customdata[0]:.1f}%%"
                          "<br>share in chart: %{percent:.1%}<extra></extra>",
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