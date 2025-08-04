# Exit Poll Dynamic Dashboard

This dashboard allows interactive exploration of U.S. exit poll data across multiple election years, states, and election types (General or Primary). Users can filter by year, state, party, and demographic variables to dynamically visualize response distributions and trends.

## Features

- View exit poll data from **multiple election cycles**
- Filter by:
  - **Year**
  - **Election type** (General or Primary)
  - **Locality type** (National vs. State)
  - **Party** (for Primaries)
- Group responses by any available demographic or issue-based variable
- Choose between **Count** and **Percentage** views
- Exportable summary tables

## Live Dashboard

> Access the dashboard live here: [https://exit-poll-dashboard.onrender.com/](https://exit-poll-dashboard.onrender.com/)

## Motivation

Exit polls are a valuable snapshot of voter behavior and political sentiment on election day. However, currently there exists no comprehensive data set where you can view repsonses across years. This tool helps to fill that gap. The audience is researchers, journalists, and election analysts examine how various groups voted across states and time.

## Data Structure

The dashboard uses a structured directory of labeled exit poll data, standardized across:

- **Years** (e.g., 2008, 2012, 2016, 2020, 2024)
- **Election types**: `General/` or `Primary/`
- **Locality**: `National/` or `State/`
- **Files** are preprocessed `.csv` versions of `.sav` and `.por` SPSS data files

Metadata for compatible variables across elections is stored in:
```
data/master_variable_index_enhanced.json
```

## Tech Stack

- **Python** with [Dash](https://dash.plotly.com/) and [Plotly](https://plotly.com/)
- **Pandas** for data manipulation
- **pyreadstat** to read SPSS `.sav` and `.por` files

## Installation

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


## Acknowledgments

- NBC News Decision Desk & the Exit Poll team
- Exit poll data from National Election Poll (ABC, CBS, NBC, CNN) and Edison Research
- Stephanie Perry, Dr. Marc Meredith, and Dr. Sharath Chandra Guntuku (mentors and advisors)

