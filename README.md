# 🗳️ Exit Poll Dynamic Dashboard

This dashboard allows interactive exploration of U.S. exit poll data across multiple election years, states, and election types (General or Primary). Users can filter by year, state, party, and demographic variables to dynamically visualize response distributions and trends.

## 📊 Features

- View exit poll data from **multiple election cycles**
- Filter by:
  - **Year**
  - **Election type** (General or Primary)
  - **Locality type** (National vs. State)
  - **Party** (for Primaries)
- Group responses by any available demographic or issue-based variable
- Choose between **Count** and **Percentage** views
- Exportable summary tables

## 🚀 Live Demo

> ⚠️ _(Optional if deployed)_  
> Access the dashboard live here: [https://your-app-url.onrender.com](https://your-app-url.onrender.com)

## 🧠 Motivation

Exit polls are a valuable snapshot of voter behavior and political sentiment on election day. However, they are often siloed and difficult to explore across cycles. This tool helps researchers, journalists, and election analysts examine how various groups voted across states and time.

## 📁 Data Structure

The dashboard uses a structured directory of labeled exit poll data, standardized across:

- **Years** (e.g., 2008, 2012, 2016, 2020, 2024)
- **Election types**: `General/` or `Primary/`
- **Locality**: `National/` or `State/`
- **Files** are preprocessed `.csv` versions of `.sav` and `.por` SPSS data files

Metadata for compatible variables across elections is stored in:
```
data/master_variable_index_enhanced.json
```

## 🛠️ Tech Stack

- **Python** with [Dash](https://dash.plotly.com/) and [Plotly](https://plotly.com/)
- **Pandas** for data manipulation
- **pyreadstat** to read SPSS `.sav` and `.por` files
- **Render** for deployment (free or paid tiers)

## 📦 Installation

### 1. Clone the repo
```bash
git clone https://github.com/your-username/exit-poll-dashboard.git
cd exit-poll-dashboard
```

### 2. Set up environment
```bash
python -m venv venv
source venv/bin/activate   # or venv\Scripts\activate on Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python app.py
```

Visit [http://localhost:8050](http://localhost:8050) in your browser.

## 🧪 Development Tips

- To preprocess raw SPSS files into clean CSVs, run:
  ```bash
  python scripts/preprocess_exit_poll_files.py
  ```

- The dashboard relies on `data/datafile_paths_dynamic.csv` to index files for use.

## 🤝 Acknowledgments

- NBC News Decision Desk & the Exit Poll team  
- Stephanie Perry, Dr. Marc Meredith, and Dr. Sharath Chandra Guntuku (mentors and advisors)

## 📜 License

MIT License. See `LICENSE` file.
