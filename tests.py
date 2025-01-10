import pandas as pd
import numpy as np

# Load the datasets
scraped = pd.read_csv('/Users/daphnehansell/Documents/GitHub/slspc/zip_30_amount - scraped_SLSPC.csv')
merged = pd.read_csv('/Users/daphnehansell/Documents/GitHub/slspc/merged_results_with_slspc.csv')

# 1. Consistency Check
rating_area_counts = merged.groupby(['state', 'rating_area'])['slspc'].nunique()
inconsistent_areas = rating_area_counts[rating_area_counts > 1]
print("Rating areas with multiple SLSPC values:")
print(inconsistent_areas if len(inconsistent_areas) > 0 else "None found")

# 2. Original Data Verification
scraped['Zip'] = scraped['Zip'].astype(str).str.zfill(5)
scraped['Unsubsidized Cost'] = scraped['Unsubsidized Cost'].str.replace(',', '').astype(float)
original_vs_merged = merged[merged['zip_code'].isin(scraped['Zip'])]
original_values = dict(zip(scraped['Zip'], scraped['Unsubsidized Cost']))
original_vs_merged['original_value'] = original_vs_merged['zip_code'].map(original_values)
mismatches = original_vs_merged[original_vs_merged['slspc'] != original_vs_merged['original_value']]
print("\nMismatched values between original and merged:")
print(mismatches[['zip_code', 'slspc', 'original_value']] if len(mismatches) > 0 else "None found")

# 3. Missing Value Check
missing_values = merged[merged['slspc'].isna()]
print("\nRows with missing SLSPC values:")
print(len(missing_values))

# 4. Statistical Reasonableness
state_stats = merged.groupby('state').agg({
    'slspc': ['count', 'min', 'max', 'mean', 'std']
}).round(2)
print("\nSummary statistics by state:")
print(state_stats)

# 5. Check for extreme outliers within states
def find_outliers(group):
    mean = group['slspc'].mean()
    std = group['slspc'].std()
    return group[abs(group['slspc'] - mean) > 3 * std]

outliers = merged.groupby('state').apply(find_outliers)
print("\nOutliers (>3 std from state mean):")
print(outliers[['state', 'rating_area', 'zip_code', 'slspc']] if len(outliers) > 0 else "None found")