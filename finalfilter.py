import pandas as pd
from pathlib import Path

def generate_county_csv(input_csv: str, output_csv: str) -> None:
    """
    Generate a CSV file containing unique counties and their information.
    
    Args:
        input_csv (str): Path to the input CSV file
        output_csv (str): Path to save the output CSV file
    """
    # Read the CSV file
    df = pd.read_csv(input_csv)
    
    # Group by state and county to get unique entries
    # We'll use the first occurrence of each county for its information
    county_data = df.groupby(['state', 'county_standardized']).agg({
        'stcountyfp': 'first',
        'rating_area': 'first'
    }).reset_index()
    
    # Ensure stcountyfp is properly formatted
    county_data['stcountyfp'] = county_data['stcountyfp'].astype(str).str.zfill(5)
    
    # Sort by state and county
    county_data = county_data.sort_values(['state', 'county_standardized'])
    
    # Create output directory if it doesn't exist
    output_path = Path(output_csv)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to CSV file
    county_data.to_csv(output_csv, index=False)

def main():
    # Use the specific file path
    input_file = "/Users/daphnehansell/Documents/GitHub/slspc/merged_results_v9.csv"
    output_file = "/Users/daphnehansell/Documents/GitHub/slspc/county_ratings.csv"
    
    try:
        generate_county_csv(input_file, output_file)
        print(f"Successfully generated {output_file}")
        
        # Print some basic statistics
        df = pd.read_csv(input_file)
        unique_counties = df.groupby(['state', 'county_standardized']).size().reset_index()
        print(f"\nTotal number of unique counties: {len(unique_counties)}")
        print(f"Number of states: {len(df['state'].unique())}")
        
    except Exception as e:
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    main()