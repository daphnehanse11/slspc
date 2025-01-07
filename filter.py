import pandas as pd

def create_filtered_dataset(input_file):
    """
    Create a filtered dataset with one ZIP code per rating area per state.
    
    Args:
        input_file (str): Path to the merged results CSV
        
    Returns:
        pd.DataFrame: Filtered dataset with one ZIP per rating area
    """
    # Read the merged results
    df = pd.read_csv(input_file)
    
    # Get first ZIP code for each state-rating area combination
    filtered_df = df.groupby(['state', 'rating_area']).agg({
        'zip_code': 'first'
    }).reset_index()
    
    # Ensure ZIP codes are 5 digits
    filtered_df['zip_code'] = filtered_df['zip_code'].astype(str).str.zfill(5)
    
    # Create CSV for scraper (just ZIP codes)
    filtered_df[['zip_code']].to_csv('zips_to_scrape.csv', index=False)
    
    # Save full filtered dataset for reference
    filtered_df.to_csv('filtered_dataset.csv', index=False)
    
    return filtered_df

def map_results_back(original_file, scraped_results_file):
    """
    Map the scraped results back to all ZIP codes.
    
    Args:
        original_file (str): Path to original merged results CSV
        scraped_results_file (str): Path to CSV with scraped data
        
    Returns:
        pd.DataFrame: Complete dataset with mapped results
    """
    # Read original dataset and scraped results
    original_df = pd.read_csv(original_file)
    scraped_df = pd.read_csv(scraped_results_file)
    
    # Create mapping dictionary from scraped results
    # Assuming scraped_results has columns: state, zip_code, unsubsidized_cost
    mapping_df = pd.merge(
        scraped_df,
        original_df[['zip_code', 'state', 'rating_area']].drop_duplicates(),
        on=['zip_code', 'state']
    )
    
    cost_mapping = mapping_df.set_index(['state', 'rating_area'])['unsubsidized_cost'].to_dict()
    
    # Map costs back to original dataset
    original_df['unsubsidized_cost'] = original_df.apply(
        lambda row: cost_mapping.get((row['state'], row['rating_area'])), 
        axis=1
    )
    
    # Save final results
    original_df.to_csv('final_results.csv', index=False)
    
    return original_df

# Example usage
if __name__ == "__main__":
    # Step 1: Create filtered dataset for scraping
    filtered_df = create_filtered_dataset('merged_results_v9.csv')
    print(f"Created filtered dataset with {len(filtered_df)} ZIP codes to scrape")
    
    # After running the scraper...
    
    # Step 2: Map results back to all ZIP codes
    # final_df = map_results_back('merged_results_v9.csv', 'scraped_results.csv')
    # print(f"Mapped results to {len(final_df)} ZIP codes")