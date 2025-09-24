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

def prepare_grouped_data(df, denom, num, mode, orientation, weight_col,
                         hide_missing=True, hide_excluded=True):
    if df[weight_col].dtype == object:
        df[weight_col] = pd.to_numeric(df[weight_col], errors='coerce')

    if mode == "percent":
        # --- group without dropping NaNs or excluded values ---
        grouped = (
            df.groupby([denom, num], dropna=False)[weight_col]
              .sum()
              .reset_index()
        )

        key = denom if orientation == "vertical" else num
        grouped[weight_col] = pd.to_numeric(grouped[weight_col], errors="coerce")

        # --- compute percentages including NaNs and excluded values ---
        totals = grouped.groupby(key, dropna=False)[weight_col].transform('sum')
        grouped["Percentage"] = (grouped[weight_col] / totals * 100).round(0)

        # --- hide excluded + missing only AFTER computation ---
        mask_excluded = grouped[denom].isin(EXCLUDE_VALUES) | grouped[num].isin(EXCLUDE_VALUES)
        mask_missing = grouped[denom].isna() | grouped[num].isna()

        final = grouped.copy()

        if hide_excluded:
            mask_excluded = (
                    final[denom].isin(EXCLUDE_VALUES) |
                    final[num].isin(EXCLUDE_VALUES)
            )
            final = final.loc[~mask_excluded].copy()

        if hide_missing:
            mask_missing = final[denom].isna() | final[num].isna()
            final = final.loc[~mask_missing].copy()

        return final.drop(columns=weight_col), "Percentage"

    else:  # Count mode
        grouped = (
            df.groupby([denom, num], dropna=False)
              .size()
              .reset_index(name="Count")
        )

        mask_excluded = grouped[denom].isin(EXCLUDE_VALUES) | grouped[num].isin(EXCLUDE_VALUES)
        mask_missing = grouped[denom].isna() | grouped[num].isna()

        final = grouped.copy()
        if hide_excluded:
            final = final[~mask_excluded]
        if hide_missing:
            final = final[~mask_missing]

        return final, "Count"

def create_percent_charts(grouped, denom, num, orientation):
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

def create_count_chart(grouped, denom, num, y_col):
    fig = px.bar(
        grouped,
        x=denom,
        y=y_col,
        color=num,
        barmode="group",
        hover_data=[],
        labels={denom: "", num: "", y_col: ""}
    )

    fig.update_traces(
        hovertemplate="Count: %{y:,}<extra></extra>"
    )

    fig.update_layout(
        xaxis_title=denom,
        yaxis_title=y_col
    )

    return fig

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