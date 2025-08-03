import os
import re
import pandas as pd

ROOT_DIR = "/Users/joellegr/Documents/DATS /Classes/Thesis:Practicum/exit poll project/roper"

years = [f for f in os.listdir(ROOT_DIR) if f != '.DS_Store']
file_records = []

states_full = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware',
    'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky',
    'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi',
    'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico',
    'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania',
    'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont',
    'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming', 'District of Columbia', 'National'
]

states_abbr = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE',
    'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY',
    'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
    'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM',
    'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA',
    'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT',
    'VA', 'WA', 'WV', 'WI', 'WY', 'DC', "National"
]

full_to_abbr = {state.upper(): abbr for state, abbr in zip(states_full, states_abbr)}

pattern = re.compile(r'^.*?_([A-Za-z\s]+?)(\d{4})(?:\s+(Dem|Rep))?\.(csv|pdf)$', re.IGNORECASE)

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
                if os.path.isfile(os.path.join(folder_path, f)) and f.lower().endswith(".csv")
            ]

            for filename in os.listdir(folder_path):
                match = pattern.match(filename)
                if match:
                    state_full = match.group(1).strip().upper()
                    year = match.group(2)
                    party = match.group(3)  # May be None
                    extension = match.group(4)

                    abbr = full_to_abbr.get(state_full)
                    if abbr:
                        if election_folder == "Primary" and party:
                            new_name = f"{abbr} {party.upper()} {year}.{extension}"
                        else:
                            new_name = f"{abbr} {year}.{extension}"

                        old_path = os.path.join(folder_path, filename)
                        new_path = os.path.join(folder_path, new_name)
                        os.rename(old_path, new_path)
                        print(f"Renamed: {filename} → {new_name}")
                    else:
                        print(f"Skipping: {filename} (state not found)")
