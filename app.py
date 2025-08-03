# app.py
import dash
from callbacks import register_callbacks
from layout import create_layout
import os

app = dash.Dash(__name__)
app.title = "Exit Poll Dashboard"

app.layout = create_layout()

df_path = os.path.join("data", "datafile_paths_dynamic.csv")
register_callbacks(app, df_path)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(debug=True, host="0.0.0.0", port=port)