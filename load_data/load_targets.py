import json

# Targets data (with quarter target and annual target)
with open("data/targets.json", "r") as f:
    targets_data = json.load(f)