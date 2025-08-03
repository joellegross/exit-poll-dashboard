# app.py
import dash
from callbacks import register_callbacks
from layout import create_layout

app = dash.Dash(__name__)
app.title = "Exit Poll Dashboard"

app.layout = create_layout()

# Register all app callbacks
df_path = "/Users/joellegr/Documents/GitHub/exit-poll-dashboard/data/datafile_paths_dynamic.csv"
register_callbacks(app, df_path)

if __name__ == "__main__":
    app.run(debug=True)