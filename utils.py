# utils.py
import pandas as pd
import numpy as np
import re
import json
import plotly.express as px
from dash import dcc, html
import os
import re


EXCLUDED_COLS = {"ID", "PRECINCT", "STANUM", "BACKSIDE", "TELEPOLL", "CALL", "CDNUM", "VERSION",
                 "ZIPCODE", "ZCODE1", "ZCODE2", "ZCODE3", "ZCODE4", "GEOCODE"}
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

def prepare_grouped_data(df, denom, num,year, weight_col=None, hide_missing=True, hide_excluded=True):
    dff = df.copy()

    if hide_missing:
        dff = dff[dff[denom].notna() & dff[num].notna()]
    if hide_excluded and 'EXCLUDED_FLAG' in dff.columns:
        dff = dff[~dff['EXCLUDED_FLAG'].astype(bool)]


    dff = dff[~dff[denom].astype(str).str.lower().eq("did not vote")]
    dff = dff[~dff[num].astype(str).str.lower().eq("did not vote")]

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

    row_c = (
        count_df.groupby(denom, dropna=False)["Count"]
        .sum()
        .reset_index()
    )
    row_c[num] = "Total"

    row_p = row_c.copy()
    row_p["Percentage"] = (
        row_p["Count"] / row_p["Count"].sum() * 100
    ).fillna(0)

    grand_c = pd.DataFrame({denom: ["Total"], num: ["Total"], "Count": [count_df["Count"].sum()]})
    grand_p = pd.DataFrame(
        {denom: ["Total"], num: ["Total"], "Percentage": [100.0], "Count": [count_df["Count"].sum()]})

    count_df = pd.concat([count_df, row_c, overall_c, grand_c], ignore_index=True)
    percent_df = pd.concat([percent_df, row_p, overall_p, grand_p], ignore_index=True)

    count_df[denom] = move_total_last(count_df[denom])
    count_df[num] = move_total_last(count_df[num])
    percent_df[denom] = move_total_last(percent_df[denom])
    percent_df[num] = move_total_last(percent_df[num])

    count_df = count_df.sort_values([denom, num]).reset_index(drop=True)
    percent_df = percent_df.sort_values([denom, num]).reset_index(drop=True)


    return count_df, percent_df


def move_total_last(series):
    vals = [v for v in series.unique() if v != "Total"] + ["Total"]
    return pd.Categorical(series, categories=vals, ordered=True)
def prepare_solo_data(df, var, year, weight_col=None, hide_missing=True, hide_excluded=True):

    dff = df.copy()

    if hide_missing:
        dff = dff[dff[var].notna()]
    if hide_excluded and "EXCLUDED_FLAG" in dff.columns:
        dff = dff[~dff["EXCLUDED_FLAG"].astype(bool)]


    dff = dff[dff[var].str.lower() != "did not vote"]


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

def create_solo_chart(percent_df, var, remainder_label="N/A", eps=1e-6, filters = None):
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
    title = ""
    if filters:
        filter_text = ", ".join([f"{k} = {v}" for k, v in filters.items()])
        title = f"<sup style='color:red;'>Filtered by {filter_text}</sup>"
    else:
        title = title

    # Keep a display column that mirrors your df for labels/tooltip
    df["__display__"] = df["Percentage"]

    fig = px.pie(
        df,
        names=var,
        values="__pct__",                 # areas (with possible remainder) → sum to 100
        hole=0.5,
        color=var,
        title = title,
        color_discrete_map=color_map,
        custom_data=["__display__"]       # your original df percentages for tooltip/labels
    )

    # Labels = df %, Tooltip = df % + normalized chart share
    fig.update_traces(
        texttemplate="%{customdata[0]:.0f}%",
        hovertemplate="%{label}"
                      "<br> %{percent:.1%}<extra></extra>",
        sort=False,
    )

    fig.update_layout(
        margin=dict(t=50, b=50, l=50, r=50),
        showlegend=True,
        title_font=dict(size=24),

    )

    return dcc.Graph(figure=fig)


def is_age_var(name: str) -> bool:
    return isinstance(name, str) and "age" in name.lower()

def age_key(label):
    s = str(label).strip().lower().replace("–", "-").replace("—", "-")
    m = re.match(r"under\s*(\d+)", s)
    if m: return (0, int(m.group(1)) - 1)
    m = re.match(r"(\d+)\s*-\s*(\d+)", s)
    if m: return (1, int(m.group(1)))
    m = re.match(r"(\d+)\s*\+|(\d+)\s*or\s*over", s)
    if m: return (2, int(m.group(1) or m.group(2)))
    m = re.match(r"(\d+)$", s)
    if m: return (1, int(m.group(1)))
    return (3, s)

def is_income_var(name: str) -> bool:
    return isinstance(name, str) and "income" in name.lower()

def _inc_to_int_dollars(txt: str) -> int:
    t = str(txt).lower().replace(",", "").replace("$", "").strip()
    m = re.match(r"^(\d+)\s*k$", t)
    if m: return int(m.group(1)) * 1000
    m = re.match(r"^\d+$", t)
    if m: return int(m.group(0))
    return 10**12

def income_key(label):
    if label is None:
        return (97, "")
    s = str(label).strip()
    if re.fullmatch(r"(?i)\s*total\s*", s):
        return (99, "total")
    sl = s.lower().replace("–", "-").replace("—", "-")
    sl = sl.replace(",", "").replace("$", "").strip()

    m = re.match(r"(?i)^(under|less\s*than)\s*(\d+)\b", sl)
    if m:
        upper = _inc_to_int_dollars(m.group(2))
        return (0, upper - 1)

    m = re.match(r"^(\d+)\s*(?:-\s*|to\s*)(\d+)\b", sl)
    if m:
        low = _inc_to_int_dollars(m.group(1))
        return (1, low)

    m = re.match(r"^(\d+)\s*(\+|or\s*(more|over))\b", sl)
    if m:
        low = _inc_to_int_dollars(m.group(1))
        return (2, low)

    m = re.match(r"^(\d+)$", sl)
    if m:
        val = _inc_to_int_dollars(m.group(1))
        return (1, val)

    return (98, sl)

# --- main function with income integrated ---

def format_table_data(grouped, denom, num, y_col, mode):
    grouped_wide = (
        grouped.pivot_table(
            index=num, columns=denom, values=y_col, aggfunc="sum", observed=False
        )
    )

    grouped_wide = grouped_wide.apply(pd.to_numeric, errors="coerce") \
                               .replace([np.inf, -np.inf], np.nan)

    # Optional: natural row sort if num looks like age or income
    if is_age_var(num):
        grouped_wide = grouped_wide.sort_index(key=lambda idx: [age_key(x) for x in idx])
    elif is_income_var(num):
        grouped_wide = grouped_wide.sort_index(key=lambda idx: [income_key(x) for x in idx])

    if mode == "percent":
        grouped_wide = grouped_wide.fillna(0).round(0).astype("Int64")
        grouped_wide = grouped_wide.astype(str) + "%"
    else:
        grouped_wide = grouped_wide.fillna(0).round(0).astype("Int64")

    df_out = grouped_wide.reset_index()
    df_out = df_out.where(pd.notna(df_out), None)

    # Determine first column
    first_col = num if num in df_out.columns else (denom if denom in df_out.columns else None)

    # Row ordering (handles Other/Omit/Total at end)
    uniques = pd.Index(df_out[first_col].dropna().unique())
    norm = uniques.map(lambda x: str(x).strip().casefold())
    special_norms = {"other", "omit", "total"}
    base_rows = uniques[~norm.isin(special_norms)].tolist()

    # Choose the right key for base row sorting
    if is_age_var(first_col) or (first_col == denom and is_age_var(denom)):
        base_rows = sorted(base_rows, key=age_key)
    elif is_income_var(first_col) or (first_col == denom and is_income_var(denom)):
        base_rows = sorted(base_rows, key=income_key)
    else:
        base_rows = sorted(base_rows, key=lambda x: str(x).lower())

    new_row_order = list(base_rows)
    for s in ["Other", "Omit", "Total"]:
        hits = uniques[norm == s.lower()]
        if len(hits):
            new_row_order.extend(hits.tolist())

    df_out = (df_out.set_index(first_col)
              .loc[new_row_order]
              .reset_index())

    # Column ordering (exclude first and specials; sort by age/income if denom)
    other_columns = [c for c in df_out.columns if c not in {first_col, "Total", "Omit", "Other"}]

    if is_age_var(denom):            # denom values are the column headers
        other_columns = sorted(other_columns, key=age_key)
    elif is_income_var(denom):
        other_columns = sorted(other_columns, key=income_key)
    else:
        other_columns = sorted(other_columns, key=lambda x: str(x).lower())

    new_column_order = ([first_col] if first_col else []) + other_columns
    if "Other" in df_out.columns:
        new_column_order += ["Other"]
    if "Omit" in df_out.columns:
        new_column_order += ["Omit"]
    if "Total" in df_out.columns:
        new_column_order += ["Total"]

    df_out = df_out[new_column_order]

    # Dash table metadata
    columns = [{"name": str(c), "id": str(c)} for c in df_out.columns]
    data = df_out.to_dict("records")
    return df_out, columns, data


def format_solo_table(grouped: pd.DataFrame, var: str, y_col: str, mode: str):
    if grouped.empty or var not in grouped.columns or y_col not in grouped.columns:
        return [], []

    df_out = grouped[[var, y_col]].copy()
    df_out[var] = df_out[var].astype(str)

    # Build/append Total
    total_val = pd.to_numeric(df_out[y_col], errors="coerce").fillna(0).sum()
    df_out = df_out[~df_out[var].str.strip().str.casefold().eq("total")]
    total_row = pd.DataFrame({var: ["Total"], y_col: [total_val]})
    df_out = pd.concat([df_out, total_row], ignore_index=True)

    # Value formatting
    if mode == "percent":
        df_out[y_col] = (
            pd.to_numeric(df_out[y_col], errors="coerce")
              .fillna(0).round(0).astype(int).astype(str) + "%"
        )
        mask_total = df_out[var].str.strip().str.casefold().eq("total")
        df_out.loc[mask_total, y_col] = "100%"
    else:
        df_out[y_col] = (
            pd.to_numeric(df_out[y_col], errors="coerce")
              .fillna(0).round(0).astype("Int64")
        )

    # Row ordering
    uniques = pd.Index(df_out[var].dropna().unique())
    norm = uniques.map(lambda x: str(x).strip().casefold())
    special_norms = {"other", "omit", "total"}

    base_rows = uniques[~norm.isin(special_norms)].tolist()

    # Key selection: age > income > alpha
    if is_age_var(var):
        base_rows = sorted(base_rows, key=age_key)
    elif is_income_var(var):
        base_rows = sorted(base_rows, key=income_key)
    else:
        base_rows = sorted(base_rows, key=lambda x: str(x).lower())

    new_row_order = list(base_rows)
    for s in ["Other", "Omit", "Total"]:
        hits = uniques[norm == s.lower()]
        if len(hits):
            new_row_order.extend(hits.tolist())

    # Apply categorical order and finalize
    df_out[var] = pd.Categorical(df_out[var], categories=new_row_order, ordered=True)
    df_out = df_out.sort_values(var).reset_index(drop=True)
    df_out = df_out.where(pd.notna(df_out), None)

    columns = [{"name": str(c), "id": str(c)} for c in df_out.columns]
    data = df_out.to_dict("records")
    return columns, data

def _norm(v):
    return None if v is None else str(v).strip().lower()

_EXCLUDE_NORM = {_norm(v) for v in EXCLUDE_VALUES}

def _is_excluded(v):
    return _norm(v) in _EXCLUDE_NORM

def create_percent_charts(percent_df, denom, num, filters):
    if denom is None or num is None or percent_df.empty:
        return html.Div()

    # Normalize text (lowercase, strip spaces)
    denom_clean = percent_df[denom].astype(str).str.lower().str.strip()
    num_clean   = percent_df[num].astype(str).str.lower().str.strip()

    # Identify and drop "total"/"omit" rows
    is_total_or_omit_denom = denom_clean.isin(["total", "omit"])
    is_total_or_omit_num   = num_clean.isin(["total", "omit"])
    percent_df = percent_df[~(is_total_or_omit_denom | is_total_or_omit_num)].copy()

    grouped = percent_df.copy()
    figures = []

    # ---------- helpers for category ordering ----------
    def order_values(values, by_var_name):
        """Return categories ordered via age_key / income_key / alpha, pushing 'Other' and 'N/A' to the end."""
        vals = list(pd.unique(pd.Series(values)))  # preserve dtype
        # normalize for special detection
        norm = [str(v).strip().casefold() for v in vals]
        specials = {"other", "n/a"}
        base = [v for v, n in zip(vals, norm) if n not in specials]

        if is_age_var(by_var_name):
            base = sorted(base, key=age_key)
        elif is_income_var(by_var_name):
            base = sorted(base, key=income_key)
        else:
            base = sorted(base, key=lambda x: str(x).lower())

        ordered = list(base)
        # append specials in fixed order if present
        for s in ["Other", "N/A"]:
            mask = [str(v).strip().casefold() == s.lower() for v in vals]
            if any(mask):
                # might be multiple spellings/cases—append all hits in original spellings
                ordered.extend([v for v, m in zip(vals, mask) if m])
        return ordered

    # Sort the facet keys (denom) for consistent chart placement
    keys_raw = grouped[denom].dropna().unique()
    if is_age_var(denom):
        keys = sorted(keys_raw, key=age_key)
    elif is_income_var(denom):
        keys = sorted(keys_raw, key=income_key)
    else:
        keys = sorted(keys_raw, key=lambda x: str(x).lower())

    # Detect candidate→party coloring as you had
    var_col = num
    var_values_all = grouped[var_col].dropna().unique()

    normalized_party_lookup = {name.lower().strip(): party for name, party in CANDIDATE_PARTY_MAP.items()}
    num_matches = sum(
        1 for v in var_values_all if isinstance(v, str) and v.lower().strip() in normalized_party_lookup
    )
    is_pres_candidate_question = num_matches >= max(1, len(var_values_all) / 2)

    if is_pres_candidate_question:
        # fixed party colors
        color_map = {}
        for name in var_values_all:
            norm_name = name.lower().strip() if isinstance(name, str) else str(name).lower().strip()
            party = normalized_party_lookup.get(norm_name, "Other")
            color_map[name] = PARTY_COLORS.get(party, PARTY_COLORS["Other"])
    else:
        # build once with a deterministic order based on the full set
        overall_order = order_values(var_values_all, var_col)
        default_colors = px.colors.qualitative.Set3 + px.colors.qualitative.Set1
        color_map = {cat: default_colors[i % len(default_colors)] for i, cat in enumerate(overall_order)}

    # ---------- build one pie per denom key ----------
    for key_val in keys:
        filtered = grouped.loc[grouped[denom] == key_val].copy()
        if filtered.empty:
            continue

        title = str(key_val)
        if filters:
            filter_text = ", ".join([f"{k} = {v}" for k, v in filters.items()])
            title = f"{title}<br><sup style='color:red;'>Filtered by {filter_text}</sup>"

        # Fill to 100% with N/A if needed (kept as a special at the end)
        subtotal = float(filtered["Percentage"].sum())
        leftover = max(0.0, round(100.0 - subtotal, 0))
        if leftover > 0:
            filtered = pd.concat(
                [filtered, pd.DataFrame([{denom: key_val, var_col: "N/A", "Percentage": leftover}])],
                ignore_index=True
            )

        # ORDER the slice categories for this pie
        present_order = order_values(filtered[var_col].dropna().unique(), var_col)
        # apply order to data for pie + legend
        filtered[var_col] = pd.Categorical(filtered[var_col], categories=present_order, ordered=True)
        filtered = filtered.sort_values(var_col)

        fig = px.pie(
            filtered,
            names=var_col,
            values="Percentage",
            hole=0.5,
            title=title,
            color=var_col,
            color_discrete_map=color_map,
            category_orders={var_col: present_order},  # enforce legend order
        )

        fig.update_traces(
            text=[f"{round(v)}%" if v > 0 else "" for v in filtered["Percentage"]],
            textinfo="text",
            hovertemplate="%{label}: %{value:.1f}%<extra></extra>",
            sort=False,  # keep our custom order
        )

        fig.update_layout(
            legend=dict(x=1.2, y=0.5, xanchor="left", orientation="v", font=dict(size=12)),
            margin=dict(t=50, b=50, l=50, r=150),
            title_font=dict(size=24)
        )

        figures.append(
            dcc.Graph(figure=fig, style={"display": "inline-block", "width": "32%", "height": "400px"})
        )

    return html.Div(figures, style={"display": "flex", "flexWrap": "wrap", "gap": "20px"})