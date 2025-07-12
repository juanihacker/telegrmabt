import json
import os

BLACKLIST_PATH = "blacklist.json"

# Load or create blacklist
if os.path.exists(BLACKLIST_PATH):
    with open(BLACKLIST_PATH, "r", encoding="utf-8") as f:
        try:
            blacklist = json.load(f)
        except json.JSONDecodeError:
            blacklist = []
else:
    blacklist = []

# Ask for DNI
dni = input("Enter the DNI to add to the blacklist: ").strip()

# Validate DNI
if not dni.isdigit():
    print("DNI must be numeric.")
    exit()

# Check if already in blacklist
if dni in blacklist:
    print("DNI is already in the blacklist.")
else:
    blacklist.append(dni)
    with open(BLACKLIST_PATH, "w", encoding="utf-8") as f:
        json.dump(blacklist, f, indent=4, ensure_ascii=False)
    print("DNI added successfully to the blacklist.")
