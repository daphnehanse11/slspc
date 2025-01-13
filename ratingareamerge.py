import pandas as pd
import numpy as np

def merge_kff_data(kff_file_path, zip_mapping_path, output_path):
    """
    Merge KFF data with ZIP code mapping and create output with state, rating area, and cost.
    """
    
    # Read the input files
    print("Reading input files...")
    kff_data = pd.read_csv(kff_file_path)
    zip_mapping = pd.read_csv(zip_mapping_path)
    
    print(f"\nInitial data shapes:")
    print(f"KFF data: {kff_data.shape} rows")
    print(f"ZIP mapping: {zip_mapping.shape} rows")
    
    # Convert ZIP codes to strings with leading zeros in both dataframes
    kff_data['Zip'] = kff_data['Zip'].astype(str).str.zfill(5)
    zip_mapping['zip_code'] = zip_mapping['zip_code'].astype(str).str.zfill(5)
    
    # Remove duplicate ZIP code entries in mapping file
    zip_mapping_clean = zip_mapping.drop_duplicates(subset=['zip_code', 'state', 'rating_area'])
    print(f"\nAfter removing duplicates in mapping: {zip_mapping_clean.shape} rows")
    
    # Check for ZIPs that still map to multiple state/rating areas
    zip_analysis = zip_mapping_clean.groupby('zip_code').agg({
        'state': lambda x: list(set(x)),
        'rating_area': lambda x: list(set(x))
    })
    multiple_mappings = zip_analysis[zip_analysis['state'].apply(len) > 1]
    
    if not multiple_mappings.empty:
        print("\nAfter cleaning, still found ZIPs that map to multiple state/rating areas:")
        print("\nExample problematic ZIP codes:")
        print(multiple_mappings.head())
        print(f"\nTotal problematic ZIPs: {len(multiple_mappings)}")
    
    # For ZIPs in our KFF data that have multiple mappings, show the details
    kff_zips_with_issues = set(kff_data['Zip']).intersection(set(multiple_mappings.index))
    if kff_zips_with_issues:
        print("\nZIPs in our KFF data with multiple mappings:")
        for zip_code in sorted(kff_zips_with_issues):
            mappings = zip_mapping_clean[zip_mapping_clean['zip_code'] == zip_code]
            print(f"\nZIP: {zip_code}")
            print(mappings[['state', 'rating_area']].to_string())
    
    # Merge the dataframes on ZIP code
    print("\nMerging datasets...")
    merged_data = pd.merge(
        kff_data,
        zip_mapping_clean[['zip_code', 'state', 'rating_area']],
        left_on='Zip',
        right_on='zip_code',
        how='left'
    )
    
    print(f"After merge: {merged_data.shape} rows")
    
    # Convert Unsubsidized Cost to numeric, handling any string formatting
    merged_data['Unsubsidized Cost'] = pd.to_numeric(
        merged_data['Unsubsidized Cost'].replace(r'[\$,]', '', regex=True),
        errors='coerce'
    )
    
    # Group by state and rating area, with additional diagnostics
    print("\nAggregating data...")
    grouped = merged_data.groupby(['state', 'rating_area'])
    
    # Get counts before aggregation
    counts = grouped.size().reset_index(name='count')
    print("\nCounts by state and rating area:")
    print(counts[counts['count'] > 1].head())  # Show only groups with multiple entries
    
    # Create final result with ZIP codes
    result = grouped.agg({
        'Unsubsidized Cost': 'mean',
        'Zip': lambda x: ', '.join(sorted(set(x)))
    }).reset_index()
    
    # Round the unsubsidized cost to 2 decimal places
    result['Unsubsidized Cost'] = result['Unsubsidized Cost'].round(2)
    
    print(f"\nFinal result: {result.shape} rows")
    
    # Save the result
    result.to_csv(output_path, index=False)
    print(f"\nOutput saved to {output_path}")
    
    return result

if __name__ == "__main__":
    # File paths
    kff_file = "/Users/daphnehansell/Documents/GitHub/slspc/kff_second_lowest_cost_silver_plan_results_age_0 - kff_second_lowest_cost_silver_plan_results_age_0.csv"
    zip_mapping_file = "/Users/daphnehansell/Documents/GitHub/slspc/merged_results_v9.csv"
    output_file = "/Users/daphnehansell/Documents/GitHub/slspc/merged_kff_rating_areas.csv"
    
    # Run the merge
    result_df = merge_kff_data(kff_file, zip_mapping_file, output_file)
    
    # Display sample of results
    print("\nFirst few rows of final result:")
    print(result_df.head())