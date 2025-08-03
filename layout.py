# layout.py
from dash import dcc, html, dash_table
import pandas as pd

def create_layout():
    df = pd.read_csv("/Users/joellegr/Documents/GitHub/exit-poll-dashboard/data/datafile_paths_dynamic.csv")

    year_options = sorted(df["year"].dropna().unique(), reverse=True)
    election_options = sorted(df["election_folder"].dropna().unique())
    locality_options = sorted(df["locality_type"].dropna().unique())
    party_options = sorted(df["party"].dropna().unique())

    return html.Div([
        html.H2("Exit Poll Dynamic Dashboard"),

        html.Label("Year"),
        dcc.Dropdown(id='year-dropdown',
                     options=[{"label": y, "value": y} for y in year_options],
                     value=year_options[0]),

        html.Label("Election Type"),
        dcc.Dropdown(id='election-dropdown',
                     options=[{"label": e, "value": e} for e in election_options],
                     value=election_options[0]),

        html.Div(id="locality-container", children=[
            html.Label("Locality Type"),
            dcc.Dropdown(id='locality-dropdown',
                         options=[{"label": l, "value": l} for l in locality_options],
                         value=locality_options[0])
        ]),

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


        html.Label("Aggregation Type"),
        dcc.RadioItems(
            id="display-mode",
            options=[
                {"label": "Count", "value": "count"},
                {"label": "Percentage", "value": "percent"}
            ],
            value="count",
            inline=True
        ),

        html.Label("Orientation Type"),
        dcc.RadioItems(
            id="orientation-mode",
            options=[
                {"label": "Horizontal", "value": "horizontal"},
                {"label": "Vertical", "value": "vertical"}
            ],
            value="horizontal",
            inline=True
        ),

        html.Hr(),

        html.Label("(Group By) Column"),
        dcc.Dropdown(id="denominator-dropdown", placeholder="Select a grouping column"),

        html.Label("(Breakdown) Column"),
        dcc.Dropdown(id="numerator-dropdown", placeholder="Select a breakdown column"),

        html.Br(),
        html.H4(""),
        html.Div(id="groupby-output"),

        html.Br(),
        html.H4(""),
        html.Div([
            html.Div(id="groupby-table-container", children=[
                dash_table.DataTable(
                    id="groupby-table",
                    columns=[],
                    data=[],
                    style_table={'overflowX': 'auto'},
                    style_cell={'textAlign': 'left', 'padding': '5px'},
                    page_size=20,
                )
            ])
        ])
    ])