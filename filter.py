import csv

def filter_zero_cost(csv_path):
    filtered_data = []
    
    # Open and read the CSV file
    with open(csv_path, 'r') as file:
        # First, let's look at the structure
        csv_reader = csv.reader(file)
        header = next(csv_reader)
        
        # Print header to see the column structure
        print("Column headers:", header)
        
        # Find the index of the cost column
        cost_column_index = None
        for i, col in enumerate(header):
            if 'cost' in col.lower() or 'unsubsidized' in col.lower():
                cost_column_index = i
                print(f"Found cost column at index {i}: {col}")
                break
        
        if cost_column_index is None:
            raise ValueError("Could not find cost column in CSV")
            
        # Now process the rows
        for row in csv_reader:
            # Debug print for the first few rows
            if len(filtered_data) < 3:  # Only print first 3 rows
                print(f"Processing row: {row}")
                
            try:
                # Make sure the row has enough columns
                if len(row) <= cost_column_index:
                    print(f"Skipping malformed row: {row}")
                    continue
                    
                # Get the cost value
                cost = row[cost_column_index].strip('"').replace(',', '')
                
                # Convert cost to float and check if it's 0
                if cost and float(cost) == 0:
                    filtered_data.append(row)
            except ValueError as e:
                print(f"Could not process row {row}: {str(e)}")
                continue
    
    return header, filtered_data

# File path
file_path = '/Users/daphnehansell/Documents/GitHub/slspc/zips_to_scrape.csv'

# Run the filter
try:
    header, filtered = filter_zero_cost(file_path)
    
    # Print results
    print("\nResults:")
    print(','.join(header))
    for row in filtered:
        print(','.join(row))
        
except FileNotFoundError:
    print(f"Error: Could not find file at {file_path}")
except Exception as e:
    print(f"Error occurred: {str(e)}")
    import traceback
    traceback.print_exc()