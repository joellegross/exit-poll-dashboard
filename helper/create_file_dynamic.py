import os
import re
import pandas as pd

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..", "data")  # relative path to /data folder

general_pattern = re.compile(
    r"(?P<id>\d+_)?(?P<state>[A-Za-z\s]+?)\s*(?P<year>19\d{2}|20\d{2})\s*(?P<party>(Dem|Rep|Democratic|Republican))?",
    re.IGNORECASE
)

primary_pattern = re.compile(
    r"(?P<id>\d+_)?(?P<state>[A-Za-z\s]+?)\s+"
    r"(?:(?P<party1>Dem|Rep|Democratic|Republican)\s+)?"
    r"(?P<year>20\d{2})"
    r"(?:\s+(?P<party2>Dem|Rep|Democratic|Republican))?",
    re.IGNORECASE
)

def normalize_party(party_raw):
    if not party_raw:
        return None
    party_clean = party_raw.lower()
    if "dem" in party_clean:
        return "DEM"
    elif "rep" in party_clean:
        return "REP"
    return party_raw.upper()

records = []

for year in os.listdir(ROOT_DIR):
    year_path = os.path.join(ROOT_DIR, year)
    if not os.path.isdir(year_path):
        continue

    for election_folder in ["General", "Primary"]:
        for locality_type in ["National", "State"] if election_folder == "General" else [None]:
            sub_path = [year_path, election_folder]
            if locality_type:
                sub_path.append(locality_type)
            folder_path = os.path.join(*sub_path)

            if not os.path.exists(folder_path):
                continue

            for fname in os.listdir(folder_path):
                if not fname.endswith(".csv") or fname == ".DS_Store":
                    continue

                full_path = os.path.join(folder_path, fname)
                rel_path = os.path.relpath(full_path, start=os.path.dirname(__file__))  # ✅ Relative!

                match = (
                    primary_pattern.search(fname)
                    if election_folder == "Primary"
                    else general_pattern.search(fname)
                )

                if match:
                    state = match.group("state").strip()
                    file_year = match.group("year")
                    party_raw = match.group("party1") or match.group("party2") if election_folder == "Primary" else None
                    party = normalize_party(party_raw)

                    records.append({
                        "state": state,
                        "year": file_year,
                        "election_folder": election_folder,
                        "locality_type": locality_type if locality_type else "N/A",
                        "party": party,
                        "path": rel_path  # ✅ Store relative path
                    })

df = pd.DataFrame(records)
df.to_csv(os.path.join(os.path.dirname(__file__), "..", "data", "datafile_paths_dynamic.csv"), index=False)