import os
import re
import pandas as pd

ROOT_DIR = "/Users/joellegr/Documents/GitHub/exit-poll-dashboard/data"

years = [f for f in os.listdir(ROOT_DIR) if f != '.DS_Store']
file_records = []

# Regex for General elections: state + year

general_pattern = re.compile(
    r"(?P<id>\d+_)?(?P<state>[A-Za-z\s]+?)\s*(?P<year>19\d{2}|20\d{2})\s*(?P<party>(Dem|Rep|Democratic|Republican))?",
    re.IGNORECASE
)

# Regex for Primary elections: state + party + year (party must appear before year)
primary_pattern = re.compile(
    r"(?P<id>\d+_)?(?P<state>[A-Za-z\s]+?)\s+"
    r"(?:(?P<party1>Dem|Rep|Democratic|Republican)\s+)?"
    r"(?P<year>20\d{2})"
    r"(?:\s+(?P<party2>Dem|Rep|Democratic|Republican))?",
    re.IGNORECASE
)

# Optional normalization
def normalize_party(party_raw):
    if not party_raw:
        return None
    party_clean = party_raw.lower()
    if "dem" in party_clean:
        return "DEM"
    elif "rep" in party_clean:
        return "REP"
    else:
        return party_raw.upper()

# Main loop
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
                if f != '.DS_Store' and f.endswith(".csv") and os.path.isfile(os.path.join(folder_path, f))
            ]

            for filepath in files:
                filename = os.path.basename(filepath)

                # Use appropriate pattern
                match = primary_pattern.search(filename) if election_folder == "Primary" else general_pattern.search(filename)

                if match:
                    state = match.group("state").strip()
                    file_year = match.group("year")
                    party_raw = match.group("party1") or match.group("party2") if election_folder == "Primary" else None
                    party = normalize_party(party_raw)

                    file_records.append({
                        "state": state,
                        "year": file_year,
                        "election_folder": election_folder,
                        "locality_type": locality_type if locality_type else "N/A",
                        "party": party,
                        "path": filepath
                    })

                    print(f"✔ Found: {state} {file_year} | Folder: {election_folder} | Party: {party or 'N/A'}")
                else:
                    print(f"✖ Filename does not match expected format: {filename}")

# Save as DataFrame
file_df = pd.DataFrame(file_records)
file_df.to_csv(
    "/Users/joellegr/Documents/GitHub/exit-poll-dashboard/data/datafile_paths_dynamic.csv",
    index=False
)