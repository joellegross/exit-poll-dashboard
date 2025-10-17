from dash import dcc, html, dash_table
import pandas as pd
import os


def create_layout():
    df_path = os.path.join("data", "datafile_paths_dynamic.csv")
    df = pd.read_csv(df_path)

    #year_options = sorted(df["year"].dropna().unique(), reverse=True)
    year_options = [2017, 2021]
    election_options = sorted(df["election_folder"].dropna().unique())
    #locality_options = sorted(df["locality_type"].dropna().unique())
    locality_options = ["State"]
    party_options = sorted(df["party"].dropna().unique())

    return html.Div([
        html.H2("Exit Poll Dynamic Dashboard", style={"marginBottom": "1rem"}),

        html.Div(className="filter-row", children=[
            html.Div([
                html.Label("Year"),
                dcc.Dropdown(id='year-dropdown',
                             options=[{"label": y, "value": y} for y in year_options],
                             value=year_options[0])
            ], className="inline-filter"),

            html.Div([
                html.Label("Election Type"),
                dcc.Dropdown(id='election-dropdown',
                             options=[{"label": e, "value": e} for e in election_options],
                             value=election_options[0])
            ], className="inline-filter"),

            html.Div(id="locality-container", children=[
                html.Label("Locality Type"),
                dcc.Dropdown(id='locality-dropdown',
                             options=[{"label": l, "value": l} for l in locality_options],
                             value=locality_options[0])
            ], className="inline-filter"),
        ]),

        html.Div(className="filter-container", children=[
            html.Div(id="state-container", children=[
                html.Label("State"),
                dcc.Dropdown(id='state-dropdown', placeholder="Select a state")
            ]),

            html.Div(id="party-container", children=[
                html.Label("Party (Primaries Only)"),
                dcc.Dropdown(id='party-dropdown',
                             options=[{"label": p, "value": p} for p in party_options],
                             placeholder="Select a party")
            ]),

            html.Div([
                html.Label("Select Variable #1"),
                dcc.Dropdown(id="var1-dropdown", placeholder="Select first variable")
            ]),

            html.Div([
                html.Label("Select Variable #2"),
                dcc.Dropdown(id="var2-dropdown", placeholder="Select second variable")
            ]),
        ]),
        html.Hr(),

        html.Div(
            id="denominator-choice-container",
            children=[
                html.Label("Select denominator:"),
                dcc.RadioItems(id="denom-choice", inline=True)
            ],
            style={"display": "none"}
        ),
        html.Div(
            id="condition-container",
            children=[
                html.Label("Filter by (optional)"),
                dcc.Dropdown(
                    id="filter-var-dropdown",
                    options=[],
                    placeholder="Choose a variable",
                ),
                dcc.Dropdown(
                    id="filter-value-dropdown",
                    options=[],
                    placeholder="Choose a value",
                ),
                dcc.Store(id="filters-store", data={}, storage_type="session"),
            ],
            style={"display": "none"}  # hidden by default
        ),
        html.Div(id="charts"),

        html.Br(),
        html.Div(id="groupby-output"),
        html.Br(),
        html.Div(
            id="agg-container",
            children=[
                html.Hr(),
                html.Div("Aggregation Type"),
                dcc.RadioItems(
                    id="agg-mode",
                    options=[{"label": "Count", "value": "count"},
                             {"label": "Percentage", "value": "percent"}],
                    value="count",
                    inline=True,
                ),
            ],
            style={"display": "none"},  # hide initially
        ),
        html.Br(),
        html.Div(
            id="groupby-table-container",
            children=[
                dash_table.DataTable(
                    id="groupby-table",
                    columns=[],
                    data=[],
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '5px',
                        'fontSize': '14px',
                    },
                    style_data_conditional=[
                        {
                            "if": {"filter_query": '{denom} = "Total"'},
                            "backgroundColor": "#f2f2f2",
                            "fontWeight": "bold",
                        },
                        {
                            "if": {"filter_query": '{num} = "Total"'},
                            "backgroundColor": "#f2f2f2",
                            "fontWeight": "bold",
                        },
                        {
                            "if": {"filter_query": '{denom} = "Total" && {num} = "Total"'},
                            "backgroundColor": "#e0e0e0",
                            "fontWeight": "bold",
                        },
                    ],
                    page_size=20,
                )
        ]),

        html.Div(
            id="sample-size-container",
            style={"marginTop": "10px", "fontStyle": "italic"}
        ),
    ])
