import os
import json
import re
from collections import defaultdict
import pandas as pd

# === Update this to your root directory ===
ROOT_DIR = "/Users/joellegr/Documents/DATS /Classes/Thesis:Practicum/exit poll project/roper"
out = '/Users/joellegr/Documents/DATS /Classes/Thesis:Practicum/exit poll project/data'

# === Initialize ===
master_dict = defaultdict(lambda: {"question": None, "occurrences": []})
year_pattern = re.compile(r"(19|20)\d{2}")
states_abbr = [  # or load from a proper list
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA', 'HI', 'ID', 'IL', 'IN',
    'IA', 'KS', 'KY', 'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV',
    'NH', 'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC', 'SD', 'TN',
    'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC', 'National'
]

# === Traverse directory ===
for root, dirs, files in os.walk(ROOT_DIR):
    for file in files:
        if not file.lower().endswith(".json"):
            continue

        filepath = os.path.join(root, file)

        # Extract metadata
        year_match = year_pattern.search(file)
        year = year_match.group(0) if year_match else "UNKNOWN"

        state = next((s for s in states_abbr if s in file), "UNKNOWN")

        election_type = "Primary" if "primary" in root.lower() or "primary" in file.lower() else \
                        "General" if "general" in root.lower() or "general" in file.lower() else \
                        "UNKNOWN"

        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"❌ Failed to read {filepath}: {e}")
            continue

        # Record each variable
        for var, question in data.items():
            if question is None:
                continue

            if master_dict[var]["question"] is None and isinstance(question, str):
                master_dict[var]["question"] = question.strip()

            master_dict[var]["occurrences"].append({
                "year": year,
                "state": state,
                "election_type": election_type,
                "file": filepath.replace(".json", ".csv")

            })

# === Optional: Save to JSON ===
output_path = os.path.join(out, "master_variable_index_enhanced.json")
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(master_dict, f, indent=2)

print(f"✅ Enhanced master variable dictionary created with {len(master_dict)} variables.")
path = '/Users/joellegr/Documents/DATS /Classes/Thesis:Practicum/exit poll project/data/master_variable_index_enhanced.json'

with open(path, "r", encoding="utf-8") as f:
    master_dict = json.load(f)

# Preview one entry
first_key = next(iter(master_dict))
print(f"🔑 First variable: {first_key}")
print(json.dumps(master_dict[first_key], indent=2))

rows = []
for var, entry in master_dict.items():
    question = entry.get("question", "")
    for occ in entry.get("occurrences", []):
        rows.append({
            "variable": var,
            "question": question,
            "year": occ.get("year", ""),
            "state": occ.get("state", ""),
            "election_type": occ.get("election_type", ""),
            "file": occ.get("file", "")
        })

df_master = pd.DataFrame(rows)

df_master = df_master[
    df_master["file"].notna() &
    ~df_master["file"].str.lower().str.contains("none.csv")
]
# Preview
df_master.to_csv("/Users/joellegr/Documents/DATS /Classes/Thesis:Practicum/exit poll project/data/variables_by_year.csv")