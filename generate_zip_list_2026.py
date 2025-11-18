#!/usr/bin/env python3
"""
Generate representative ZIP code list for 2026 scraping
Based on filter3.py logic but updated for current rating areas
"""
import pandas as pd

def filter_zip_codes(input_path, output_path):
    # Read the CSV file
    df = pd.read_csv(input_path)

    # List of valid states (50 states + DC)
    valid_states = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DC', 'DE', 'FL',
        'GA', 'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME',
        'MD', 'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH',
        'NJ', 'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI',
        'SC', 'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'
    }

    # Filter to valid states
    df = df[df['state'].isin(valid_states)]

    # Remove rows with missing rating areas
    df = df[df['rating_area'].notna()]

    # Find ZIP codes that appear in only one county
    zip_county_counts = df.groupby('zip_code')['county_standardized'].nunique()
    single_county_zips = zip_county_counts[zip_county_counts == 1].index
    df = df[df['zip_code'].isin(single_county_zips)]

    # Group by state and rating area, then select one random ZIP code from each group
    df['state_rating_area'] = df['state'] + '_' + df['rating_area'].astype(str)

    # Use groupby and sample to select one random ZIP code per state-rating area
    sampled_df = df.groupby('state_rating_area').apply(
        lambda x: x.sample(n=1, random_state=42)
    ).reset_index(drop=True)

    # Keep only the ZIP code column and save
    final_df = pd.DataFrame({'zip_code': sampled_df['zip_code']})

    # Convert ZIP codes to strings with leading zeros
    final_df['zip_code'] = final_df['zip_code'].astype(str).str.zfill(5)

    # Save to CSV
    final_df.to_csv(output_path, index=False)

    # Print some statistics
    print(f"Total number of ZIP codes selected: {len(final_df)}")
    print(f"\nNumber of rating areas per state:")
    state_counts = sampled_df['state'].value_counts().sort_index()
    for state, count in state_counts.items():
        print(f"  {state}: {count}")

    # Show TX and ME specifically
    print(f"\nTexas rating areas: {sampled_df[sampled_df['state']=='TX']['rating_area'].nunique()}")
    print(f"Maine rating areas: {sampled_df[sampled_df['state']=='ME']['rating_area'].nunique()}")

    return final_df

if __name__ == "__main__":
    input_path = "merged_results_v9.csv"
    output_path = "zip_codes_2026.csv"

    result = filter_zip_codes(input_path, output_path)
    print(f"\nSaved to {output_path}")
    print(f"\nFirst 10 ZIP codes:")
    print(result.head(10))
