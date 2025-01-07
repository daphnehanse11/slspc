import pandas as pd
import numpy as np
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def standardize_county_name(county):
    """Standardize county names to handle common variations"""
    if pd.isna(county):
        return county
    
    county = str(county).strip()
    
    # Remove 'County' and standardize city
    county = county.replace(' County', '').replace(' city', ' City')
    county = county.replace(' Parish', '')  # For Louisiana parishes
    county = county.replace('</p>', '')  # Remove stray HTML tags
    
    # State-specific fixes
    replacements = {
        # Indiana fixes
        'Kosclusko': 'Kosciusko',
        'Deleware': 'Delaware',
        'Davless': 'Daviess',
        'Dubols': 'Dubois',
        'Marlon': 'Marion',
        
        # Illinois fixes
        'Dupage': 'DuPage',
        'De Witt': 'DeWitt',
        
        # California fixes
        'San Bernadino': 'San Bernardino',
        
        # Kansas fixes
        'Chautaugua': 'Chautauqua',
        
        # North Dakota fixes
        'Trail': 'Traill',
        'Trailll': 'Traill',
        
        # Louisiana fixes
        'Vermillion': 'Vermilion',
        
        # Texas fixes
        'Culbertson': 'Culberson',
        'Ochittree': 'Ochiltree',
        'Wheiler': 'Wheeler',
        
        # Wisconsin fixes
        'LaFayette': 'Lafayette',
        
        # Georgia fixes
        'Heralson': 'Haralson',
        'DeKalb': 'De Kalb',
    
        # Florida fixes
        'Desoto': 'DeSoto',
        
        # Minnesota fixes
        'Lac Qui Parle': 'Lac qui Parle',
        'Lac qui Parle': 'Lac qui Parle',
        
        # Ohio fixes
        'Galia': 'Gallia',
        
        # South Dakota fixes
        'Mc Cook': 'McCook',
        'Bonn Homme': 'Bon Homme',
        'DeBaca': 'De Baca',
        
        # Common variations
        'Saint': 'St.',
        'St ': 'St. '
    }
    
    for old, new in replacements.items():
        county = county.replace(old, new)
    
    return county.strip()

def merge_rating_areas(zip_county_df, areas_df):
    """
    Merge ZIP codes with rating areas using both county-based and ZIP3-based matching
    """
    # Make copies to avoid modifying original dataframes
    zip_county_df = zip_county_df.copy()
    areas_df = areas_df.copy()
    
    # Store original county names for reference
    zip_county_df['ORIGINAL_COUNTYNAME'] = zip_county_df['COUNTYNAME']
    
    # Initialize result DataFrame
    result = zip_county_df[['ZIP', 'COUNTYNAME', 'ORIGINAL_COUNTYNAME', 'STATE', 'STCOUNTYFP', 'CLASSFP']].copy()
    result.columns = ['zip_code', 'county_standardized', 'county_original', 'state', 'stcountyfp', 'classfp']
    
    # Ensure ZIP codes are strings before extracting ZIP3
    result['zip_code'] = result['zip_code'].astype(str).str.zfill(5)
    result['ZIP3'] = result['zip_code'].str[:3]
    result['rating_area'] = np.nan
    
    # First handle territories - they all get rating area 1
    territories = ['GU', 'VI', 'PR', 'AS', 'MP']
    territory_mask = result['state'].isin(territories)
    result.loc[territory_mask, 'rating_area'] = '1'
    
    # For non-territory states, proceed with regular matching
    non_territory_mask = ~result['state'].isin(territories)
    non_territory_records = result[non_territory_mask]
    
    # Standardize county names for non-territory records
    non_territory_records['county_standardized'] = non_territory_records['county_standardized'].apply(standardize_county_name)
    areas_df['COUNTY_ZIP3'] = areas_df['COUNTY_ZIP3'].apply(standardize_county_name)
    
    # Create mapping dictionary for ZIP3-based areas
    zip3_mapping = {}
    for _, row in areas_df.iterrows():
        if str(row['COUNTY_ZIP3']).isdigit():
            zip3_mapping[(row['STATE'], row['COUNTY_ZIP3'])] = row['AREA']
    
    # Create mapping for county-based areas
    county_mapping = {}
    for _, row in areas_df.iterrows():
        if not str(row['COUNTY_ZIP3']).isdigit():
            county_mapping[(row['STATE'], row['COUNTY_ZIP3'])] = row['AREA']
    
    # Process non-territory records
    for idx, row in non_territory_records.iterrows():
        # Handle Los Angeles ZIP3s specially
        if row['state'] == 'CA':
            if row['ZIP3'] in ['906', '907', '908', '910', '911', '912', '915', '917', '918', '935']:
                result.at[idx, 'rating_area'] = '15'
            elif row['ZIP3'] in ['900', '902', '903', '904', '905', '913', '914', '916', '923', '928', '932']:
                result.at[idx, 'rating_area'] = '16'
                continue
        
        # Try ZIP3-based matching
        key = (row['state'], row['ZIP3'])
        if key in zip3_mapping:
            result.at[idx, 'rating_area'] = zip3_mapping[key]
            continue
            
        # Try county-based matching
        key = (row['state'], row['county_standardized'])
        if key in county_mapping:
            result.at[idx, 'rating_area'] = county_mapping[key]
    
    # Generate report
    total_records = len(result)
    matched_records = result['rating_area'].notna().sum()
    print(f"\nMatching Results:")
    print(f"Total records: {total_records}")
    print(f"Successfully matched: {matched_records}")
    print(f"Success rate: {(matched_records/total_records)*100:.2f}%")
    
    # Get unmatched records
    unmatched = result[result['rating_area'].isna()].copy()
    
    if not unmatched.empty:
        print("\nUnmatched records by state:")
        state_counts = unmatched['state'].value_counts()
        print(state_counts)
        
        # Save all unmatched records
        unmatched_sorted = unmatched.sort_values(['state', 'county_original', 'zip_code'])
        
        # Create comparison with rating areas file
        rating_areas_counties = areas_df[~areas_df['COUNTY_ZIP3'].str.isdigit()].copy()
        rating_areas_counties = rating_areas_counties[['STATE', 'COUNTY_ZIP3']].rename(
            columns={'STATE': 'state', 'COUNTY_ZIP3': 'rating_area_county'})
        
        # Add column showing available counties in rating areas file
        unmatched_sorted['available_counties'] = unmatched_sorted['state'].map(
            rating_areas_counties.groupby('state')['rating_area_county'].apply(lambda x: ', '.join(sorted(set(x)))))
        
        # Select and reorder columns for output
        output_columns = [
            'state', 
            'county_original',
            'county_standardized',
            'zip_code',
            'stcountyfp',
            'classfp',
            'available_counties'
        ]
        
        unmatched_path = 'unmatched_records_9.csv'
        unmatched_sorted[output_columns].to_csv(unmatched_path, index=False)
        print(f"\nUnmatched records saved to: {unmatched_path}")
        
        # Print sample of unmatched records
        print("\nSample of unmatched records:")
        print(unmatched_sorted[output_columns].head())
    
    return result

def main():
    print("Script starting...")
    try:
        # Load data
        logger.info("Loading data files...")
        areas_df = pd.read_csv('areas.csv')
        print(f"Successfully loaded areas.csv with {len(areas_df)} rows")
        
        zip_county_df = pd.read_csv('ZIP-COUNTY-FIPS_2017-06.csv')
        print(f"Successfully loaded ZIP-COUNTY file with {len(zip_county_df)} rows")
        
        logger.info("Processing merge...")
        result_df = merge_rating_areas(zip_county_df, areas_df)
        
        # Save results
        output_path = 'merged_results_v9.csv'
        result_df.to_csv(output_path, index=False)
        print(f"\nResults saved to: {output_path}")
        
    except FileNotFoundError as e:
        print(f"Error: Could not find input file: {e}")
    except Exception as e:
        print(f"Error: An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()