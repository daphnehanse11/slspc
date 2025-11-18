#!/usr/bin/env python3
"""
Update state_rating_area_cost.yaml with 2026 SLCSP premiums
"""

import pandas as pd
import yaml
from collections import OrderedDict

# Preserve YAML order and formatting
def represent_ordereddict(dumper, data):
    return dumper.represent_mapping('tag:yaml.org,2002:map', data.items())

yaml.add_representer(OrderedDict, represent_ordereddict)

# Custom float formatter to always show .00
def float_representer(dumper, value):
    return dumper.represent_scalar('tag:yaml.org,2002:float', f'{value:.2f}')

yaml.add_representer(float, float_representer)

# Don't add custom string representer - will handle dates differently

print("Loading scraped results...")
results = pd.read_csv('zip_codes_2026_results.csv')

print("Loading rating area mapping...")
merged = pd.read_csv('merged_results_v9.csv')

# Join to get rating areas for each ZIP
print("Mapping ZIPs to rating areas...")
df = results.merge(
    merged[['zip_code', 'state', 'rating_area']],
    left_on='Zip',
    right_on='zip_code',
    how='left',
    suffixes=('', '_merged')
)

# Remove ERRORs
df = df[df['Unsubsidized Cost'] != 'ERROR']
print(f"Removed {len(results) - len(df)} ERROR entries")

# Convert costs to float
df['Unsubsidized Cost'] = pd.to_numeric(df['Unsubsidized Cost'], errors='coerce')

# Group by state and rating area - take the first cost for each area
print("Grouping by state and rating area...")
slspc_2026 = df.groupby(['State', 'rating_area'])['Unsubsidized Cost'].first().to_dict()

print(f"Found {len(slspc_2026)} state/rating area combinations")

# Load existing YAML
yaml_path = '../policyengine-us/policyengine_us/parameters/gov/aca/state_rating_area_cost.yaml'
print(f"Loading existing YAML from {yaml_path}...")

with open(yaml_path, 'r') as f:
    # Read as string to preserve header
    content = f.read()

# Split header from data
lines = content.split('\n')
header_lines = []
data_start = 0

for i, line in enumerate(lines):
    if line.strip() and not line.startswith(' ') and ':' in line and line.split(':')[0].isupper():
        # Found first state
        data_start = i
        break
    header_lines.append(line)

header = '\n'.join(header_lines)

# Parse just the data section
data_content = '\n'.join(lines[data_start:])
data = yaml.safe_load(data_content)

# Convert to OrderedDict to preserve state order
ordered_data = OrderedDict()
for state in sorted(data.keys()):
    ordered_data[state] = OrderedDict()
    # Sort areas but keep the original type (int for numeric, str for alphanumeric)
    area_keys = list(data[state].keys())
    # Separate numeric and alphanumeric keys
    numeric_keys = [k for k in area_keys if isinstance(k, int)]
    string_keys = [k for k in area_keys if isinstance(k, str)]
    # Sort each group
    sorted_keys = sorted(numeric_keys) + sorted(string_keys, key=lambda x: (int(''.join(filter(str.isdigit, x))) if any(c.isdigit() for c in x) else 0, x))

    for area in sorted_keys:
        # Convert all date keys to strings for consistent sorting
        area_dates = {}
        for date_key, value in data[state][area].items():
            if isinstance(date_key, str):
                area_dates[date_key] = value
            else:
                # Convert datetime.date to string
                area_dates[str(date_key)] = value
        ordered_data[state][area] = OrderedDict(sorted(area_dates.items()))

# Debug: Show what's in ordered_data for AK
print("\nDEBUG: AK rating areas in ordered_data:")
if 'AK' in ordered_data:
    print(f"  Keys: {list(ordered_data['AK'].keys())}")
    print(f"  Types: {[type(k) for k in ordered_data['AK'].keys()]}")
else:
    print("  AK not found!")

# Debug: Show what we're trying to match
print("\nDEBUG: First 5 areas from slspc_2026:")
for i, ((state, area), cost) in enumerate(list(slspc_2026.items())[:5]):
    print(f"  ({state}, {area}) -> type={type(area)}, cost={cost}")

# Add 2026 values
print("\nAdding 2026 values...")
added_count = 0
missing_areas = []
updated_areas = []

for (state, area), cost in slspc_2026.items():
    # Handle both numeric and alphanumeric rating areas (e.g., ME has '3N', '3S')
    # The YAML has integer keys (1, 2, 3) for numeric areas and string keys for alphanumeric ('3N', '3S')
    # The CSV data comes as strings, so we need to convert numeric strings to integers
    if isinstance(area, str):
        # Try to convert to int - if it succeeds, use int key
        try:
            area_key = int(area)
            area_display = area
        except ValueError:
            # It's alphanumeric like '3N', '3S' - keep as string
            area_key = area
            area_display = area
    elif isinstance(area, float):
        area_key = int(area)
        area_display = str(int(area))
    else:
        # Already an int
        area_key = area
        area_display = str(area)

    if state not in ordered_data:
        print(f"WARNING: State {state} not in existing YAML, skipping")
        continue

    if area_key not in ordered_data[state]:
        print(f"WARNING: Rating area {state}-{area_display} not in existing YAML, skipping")
        missing_areas.append(f"{state}-{area_display}")
        continue

    # Add 2026 value to existing rating area
    ordered_data[state][area_key]['2026-01-01'] = float(cost)
    updated_areas.append(f"{state}-{area_display}")
    added_count += 1

print(f"Added {added_count} 2026 values to existing rating areas")

if missing_areas:
    print(f"\nWARNING: {len(missing_areas)} rating areas not found in existing YAML:")
    for area in missing_areas[:20]:
        print(f"  - {area}")
    if len(missing_areas) > 20:
        print(f"  ... and {len(missing_areas) - 20} more")

# Write back
print(f"Writing updated YAML to {yaml_path}...")
with open(yaml_path, 'w') as f:
    # Write header
    f.write(header)
    if not header.endswith('\n'):
        f.write('\n')

    # Write data with proper formatting
    yaml_str = yaml.dump(ordered_data, default_flow_style=False, sort_keys=False, allow_unicode=True)
    f.write(yaml_str)

print("✓ YAML update complete!")
print(f"\nSummary:")
print(f"  - {added_count} 2026 values added to existing rating areas")
if missing_areas:
    print(f"  - {len(missing_areas)} rating areas skipped (not in existing YAML)")
print(f"  - Updated file: {yaml_path}")
