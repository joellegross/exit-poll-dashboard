import pyreadstat
import os
import re
import json

ROOT_DIR = os.path.join(os.path.dirname(__file__), "data")

states_full = [
    'Alabama', 'Alaska', 'Arizona', 'Arkansas', 'California', 'Colorado', 'Connecticut', 'Delaware',
    'Florida', 'Georgia', 'Hawaii', 'Idaho', 'Illinois', 'Indiana', 'Iowa', 'Kansas', 'Kentucky',
    'Louisiana', 'Maine', 'Maryland', 'Massachusetts', 'Michigan', 'Minnesota', 'Mississippi',
    'Missouri', 'Montana', 'Nebraska', 'Nevada', 'New Hampshire', 'New Jersey', 'New Mexico',
    'New York', 'North Carolina', 'North Dakota', 'Ohio', 'Oklahoma', 'Oregon', 'Pennsylvania',
    'Rhode Island', 'South Carolina', 'South Dakota', 'Tennessee', 'Texas', 'Utah', 'Vermont',
    'Virginia', 'Washington', 'West Virginia', 'Wisconsin', 'Wyoming', 'District of Columbia', 'Puerto Rico'
]

states_abbr = [
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE',
    'FL', 'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY',
    'LA', 'ME', 'MD', 'MA', 'MI', 'MN', 'MS',
    'MO', 'MT', 'NE', 'NV', 'NH', 'NJ', 'NM',
    'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA',
    'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VT',
    'VA', 'WA', 'WV', 'WI', 'WY', 'DC', 'PR'
]
full_to_abbr = {state.upper(): abbr for state, abbr in zip(states_full, states_abbr)}

state_id_to_name = {
    1: "Alabama", 2: "Alaska", 3: "Arizona", 4: "Arkansas", 5: "California", 6: "Colorado",
    7: "Connecticut", 8: "Delaware", 9: "District of Columbia", 10: "Florida",
    11: "Georgia", 12: "Hawaii", 13: "Idaho", 14: "Illinois", 15: "Indiana", 16: "Iowa",
    17: "Kansas", 18: "Kentucky", 19: "Louisiana", 20: "Maine", 21: "Maryland",
    22: "Massachusetts", 23: "Michigan", 24: "Minnesota", 25: "Mississippi", 26: "Missouri", 27: "Montana",
    28: "Nebraska",
    29: "Nevada", 30: "New Hampshire", 31: "New Jersey", 32: "New Mexico", 33: "New York", 34: "North Carolina",
    35: "North Dakota", 36: "Ohio", 37: "Oklahoma", 38: "Oregon", 39: "Pennsylvania",
    40: "Rhode Island", 41: "South Carolina", 42: "South Dakota", 43: "Tennessee",
    44: "Texas", 45: "Utah", 46: "Vermont", 47: "Virginia",  48: "Washington", 49: "West Virginia", 50: "Wisconsin", 51: "Wyoming",
    71 : "Puerto Rico"
}


# === Helpers ===
def apply_value_labels(df, meta):
    for col, labels in meta.variable_value_labels.items():
        if col in df.columns:
            df[col] = df[col].map(labels)
    return df

def create_question_names(meta):
    return meta.column_names_to_labels

def determine_locality(df_labeled, base_filename, year, election_folder, locality_type):
    if locality_type == "National":
        return "National"

    columns_upper = df_labeled.columns.str.upper()
    stanum_col = None
    for col in ["STANUM", "STATEID", "STATE"]:
        if col in columns_upper:
            stanum_col = col
            break

    if stanum_col:
        raw_val = df_labeled[stanum_col].iloc[0]
        value = str(raw_val).strip().upper()

        try:
            numeric_id = int(float(value))
            state_name = state_id_to_name.get(numeric_id)
            if state_name:
                return full_to_abbr.get(state_name.upper(), base_filename)
        except (ValueError, TypeError):
            pass

        # If not numeric, assume it's a full state name or abbreviation
        return full_to_abbr.get(value.upper(), base_filename)

    return base_filename

def determine_party(df_labeled, filename, year):
    if year in ["2004", "2020"]:
        return "DEM"
    elif year in ["2012", "2024"]:
        return "REP"

    match = re.search(r"(DEM|REP)", filename, re.IGNORECASE)
    if match:
        return match.group(1).upper()

    if "DEMVOTE" in df_labeled.columns:
        return "DEM"
    elif "REPVOTE" in df_labeled.columns:
        return "REP"

    return "None"


def process_file(filepath, year, election_folder, locality_type):
    filename = os.path.basename(filepath)
    base_filename = os.path.splitext(filename)[0]

    try:
        if filename.lower().endswith(".por"):
            df, meta = pyreadstat.read_por(filepath)
        else:
            df, meta = pyreadstat.read_sav(filepath)
    except Exception as e:
        print(f"❌ Error reading {filename}: {e}")
        return

    df_labeled = apply_value_labels(df.copy(), meta)

    # Special fix for 2008 Primary file
    if election_folder == "Primary" and year == "2008" and filename.endswith(".sav"):
        fix_path = os.path.join(ROOT_DIR, "2008", "Primary", "2008 GE national final data_values labeled.sav")
        _, meta_fix = pyreadstat.read_sav(fix_path)
        df_labeled = pyreadstat.set_value_labels(df_labeled, meta_fix)

    # === Local and Party Logic ===
    local = determine_locality(df_labeled, base_filename, year, election_folder, locality_type)
    json_string = "none.json"
    try:
        if election_folder == "Primary":
            party = determine_party(df_labeled, filename, year)
            final_string = f"{local} {party} {year}.csv"
        else:
            final_string = f"{local} {year}.csv"
            json_string = f"{local} {year}.json"
    except Exception as e:
        print(f"⚠️ TypeError for {filename}: {e}")
        final_string = f"{base_filename}.csv"
        json_string = f"{base_filename}.json"

    output_path = os.path.join(os.path.dirname(filepath), final_string)
    try:
        column_name_dict = create_question_names(meta)
        json_path = os.path.join(os.path.dirname(filepath), json_string)
        with open(json_path, "w") as f:
            json.dump(column_name_dict, f, indent=4)
    except TypeError as e:
        pass

    df_labeled.to_csv(output_path, index=False)

    print(f"✅ Saved: {output_path}")


# === Main Loop ===
def process_all():
    years = [f for f in os.listdir(ROOT_DIR) if not f.startswith('.')]
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

                print(f"\n📂 Scanning: {folder_path}")
                for f in os.listdir(folder_path):
                    full_path = os.path.join(folder_path, f)
                    if os.path.isfile(full_path) and f.lower().endswith((".por", ".sav")):
                        process_file(full_path, year, election_folder, locality_type)


# === Run ===
if __name__ == "__main__":
    process_all()