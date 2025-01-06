import pandas as pd

# Read the datasets
survey_df = pd.read_csv('survey.csv')
rating_areas_df = pd.read_csv('merged_results_v4.csv')

# Ensure zip codes are strings with leading zeros
survey_df['zip_code'] = survey_df['zip_code'].astype(str).str.zfill(5)
rating_areas_df['zip_code'] = rating_areas_df['zip_code'].astype(str).str.zfill(5)

# Merge datasets
result = pd.merge(
    survey_df,
    rating_areas_df[['zip_code', 'rating_area']],
    on='zip_code',
    how='left'
)

# Save the complete merged result
result.to_csv('survey_with_rating_areas.csv', index=False)

# Create and save DataFrame of records with missing rating areas
missing_ratings = result[result['rating_area'].isna()].copy()
missing_ratings.to_csv('missing_rating_areas.csv', index=False)

# Display statistics
print("\nMerge statistics:")
print(f"Original survey records: {len(survey_df)}")
print(f"Merged records: {len(result)}")
print(f"Records with missing rating areas: {len(missing_ratings)}")

# Display sample of missing records
print("\nSample of records with missing rating areas:")
print(missing_ratings[['household_id', 'state_code_str', 'zip_code', 'county_str']].head())

# Get unique states with missing rating areas
missing_states = missing_ratings['state_code_str'].value_counts()
print("\nMissing rating areas by state:")
print(missing_states)