import pandas as pd
import pyreadstat
import os
import re

ROOT_DIR = '/Users/joellegr/Documents/DATS /Classes/Thesis:Practicum/exit poll project/roper'

years = [f for f in os.listdir(ROOT_DIR)
         if f != '.DS_Store']

states_full = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware',
    'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky',
    'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi',
    'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico',
    'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania',
    'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont',
    'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming', 'District of Columbia'
]

states_abbr = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE',
    'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY',
    'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
    'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM',
    'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA',
    'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT',
    'VA', 'WA', 'WV', 'WI', 'WY', 'DC'
]

state_id_to_name = {
    1: "Alabama",
    3: "Arizona",
    4: "Arkansas",
    5: "California",
    6: "Colorado",
    7: "Connecticut",
    10: "Florida",
    11: "Georgia",
    13: "Idaho",
    14: "Illinois",
    15: "Indiana",
    16: "Iowa",
    17: "Kansas",
    18: "Kentucky",
    19: "Louisiana",
    20: "Maine",
    21: "Maryland",
    22: "Massachusetts",
    23: "Michigan",
    24: "Minnesota",
    26: "Missouri",
    28: "Nebraska",
    29: "Nevada",
    30: "New Hampshire",
    32: "New Mexico",
    33: "New York",
    34: "North Carolina",
    35: "North Dakota",
    36: "Ohio",
    37: "Oklahoma",
    38: "Oregon",
    39: "Pennsylvania",
    40: "Rhode Island",
    41: "South Carolina",
    42: "South Dakota",
    43: "Tennessee",
    44: "Texas",
    45: "Utah",
    46: "Vermont",
    48: "Washington",
    50: "Wisconsin",
    51: "Wyoming"
}


full_to_abbr = {state.upper(): abbr for state, abbr in zip(states_full, states_abbr)}


for year in years:

    for election_folder in ["General", "Primary"]:

        locality_types = ["National", "State"] if election_folder == "General" else [None]

        for locality_type in locality_types:
            folder_parts = [ROOT_DIR, year, election_folder]
            if locality_type:
                folder_parts.append(locality_type)

            folder_path = os.path.join(*folder_parts)

            if not os.path.exists(folder_path):
                continue

            print(f"📂 Scanning folder: {folder_path}")

            files = [
                os.path.join(folder_path, f)
                for f in os.listdir(folder_path)
                if os.path.isfile(os.path.join(folder_path, f)) and f.lower().endswith(".por") and "-Data" in f
            ]

            for filepath in files:
                filename = os.path.basename(filepath)
                base_filename = os.path.splitext(filename)[0]  # e.g., '02780-0011-Data'
                state_name = None
                df, meta = pyreadstat.read_por(filepath)
                df_labeled = df.copy()

                for col, value_label_dict in meta.variable_value_labels.items():
                    if col in df_labeled.columns:
                        df_labeled[col] = df[col].map(lambda x: value_label_dict.get(x))
                folder_path = os.path.dirname(filepath)

                rename_dict = {
                    col: meta.column_names_to_labels[col]
                    for col in df_labeled.columns
                    if col in meta.column_names_to_labels
                }


                df_labeled.rename(columns=rename_dict, inplace=True)
                cleaned_labels = [label if label is not None else "Unknown" for label in meta.column_labels]
                state_id_col = [col for col in cleaned_labels if "state" in col.lower()][0]
                state_id = df_labeled[state_id_col].unique()[0]
                state_name = state_id_to_name.get(int(state_id))
                print(f"{filename} → {state_name}")

                df_labeled=df_labeled.copy()
                columns_to_remove = ['1', '0', 'G']
                df_labeled = df_labeled.drop(columns=columns_to_remove, errors="ignore")

                if locality_type == "National":
                    local = "National"
                else:
                    state_abbr = full_to_abbr.get(state_name.strip().upper()) if state_name else None
                    local = state_abbr

                if not local:
                    local = "None"
                final_string = local + " " + year + ".csv"

                csv_path = os.path.join(folder_path,final_string)
                df_labeled.to_csv(csv_path, index=False)