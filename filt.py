import pandas as pd

# Read the CSV file
df = pd.read_csv('/Users/daphnehansell/Documents/GitHub/slspc/kff_second_lowest_cost_silver_plan_results.csv')

# Convert the 'Unsubsidized Cost' column to numeric, removing any commas
df['Unsubsidized Cost'] = pd.to_numeric(df['Unsubsidized Cost'].str.replace(',', ''), errors='coerce')

# Filter for rows where Unsubsidized Cost is 0
zero_cost_df = df[df['Unsubsidized Cost'] == 0]

# Display the filtered results
print(zero_cost_df)

# Optionally, save the filtered results to a new CSV file
zero_cost_df.to_csv('zero_cost_results.csv', index=False)

