import pandas as pd

# Read the CSV files
scraped_df = pd.read_csv('/Users/daphnehansell/Documents/GitHub/slspc/zip_30_amount - scraped_SLSPC.csv')
full_df = pd.read_csv('/Users/daphnehansell/Documents/GitHub/slspc/merged_results_v9.csv')

# Clean up column names and data
scraped_df = scraped_df.rename(columns={'Zip': 'zip_code', 'Unsubsidized Cost': 'slspc'})
# Remove any commas from the SLSPC values and convert to float
scraped_df['slspc'] = scraped_df['slspc'].str.replace(',', '').astype(float)

# Convert zip codes to strings with leading zeros in both dataframes
scraped_df['zip_code'] = scraped_df['zip_code'].astype(str).str.zfill(5)
full_df['zip_code'] = full_df['zip_code'].astype(str).str.zfill(5)

# Merge the scraped data with the full dataset
merged_df = full_df.merge(scraped_df[['zip_code', 'slspc']], 
                         on='zip_code', 
                         how='left')

# Create a mapping of SLSPC values for each state and rating area
slspc_mapping = merged_df.groupby(['state', 'rating_area'])['slspc'].first().reset_index()

# Fill in missing SLSPC values using the mapping
final_df = merged_df.copy()
for _, row in slspc_mapping.iterrows():
    mask = ((final_df['state'] == row['state']) & 
            (final_df['rating_area'] == row['rating_area']))
    final_df.loc[mask, 'slspc'] = row['slspc']

# Save the result to a new CSV
output_path = '/Users/daphnehansell/Documents/GitHub/slspc/merged_results_with_slspc.csv'
final_df.to_csv(output_path, index=False)

# Print some validation info
print(f"Total number of rows in original dataset: {len(full_df)}")
print(f"Total number of rows in final dataset: {len(final_df)}")
print(f"Number of unique SLSPC values: {final_df['slspc'].nunique()}")
print("\nSample of final dataset:")
print(final_df[['zip_code', 'state', 'rating_area', 'slspc']].head())