#!/usr/bin/env python3
"""
Command-line scraper for 2026 SLSPC data
Processes all ZIPs in zip_codes_2026.csv
"""
import pandas as pd
from playwright.sync_api import sync_playwright
import re
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def scrape_kff_calculator(state, zip_code, age):
    """Scrape KFF calculator for a single ZIP code"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60000)

        try:
            page.goto("https://www.kff.org/interactive/calculator-aca-enhanced-premium-tax-credit/")
            page.wait_for_selector("#subsidy-form", state="visible")

            # Fill out the form
            page.select_option("#state-dd", state.lower())
            page.fill("input[name='zip']", zip_code)
            page.fill("input[name='income']", "1000000")  # Use 1 million as income
            page.click("#employer-coverage-0")  # Assume no employer coverage
            page.select_option("#number-people", "1")  # 1-person household

            if state.upper() in ["NY", "VT"]:
                page.select_option("#number-people-alternate", "individual")
            else:
                # Always select 0 adults and 1 child
                page.select_option("#number-adults", "0")
                page.select_option("#number-children", "1")
                page.select_option("select[name='children[0][age]']", str(age))

            # Submit the form
            page.click("input[type='submit'][value='Submit']")

            # Wait for results to load
            page.wait_for_selector(".results-list", state="visible")

            # Extract the unsubsidized cost
            cost_text = page.inner_text(
                "dt:has-text('Without financial help, your silver plan would cost:') + dd"
            )
            match = re.search(r"\$(\d+,?\d*)", cost_text)
            unsubsidized_cost = match.group(1) if match else "N/A"

            browser.close()

            return {
                "State": state,
                "Zip": zip_code,
                "Age": age,
                "Unsubsidized Cost": unsubsidized_cost,
            }

        except Exception as e:
            logging.error(f"Error scraping ZIP {zip_code} in {state}: {str(e)}")
            browser.close()
            return {
                "State": state,
                "Zip": zip_code,
                "Age": age,
                "Unsubsidized Cost": "ERROR",
            }

def main():
    # Configuration
    AGE = 30

    # Load ZIP codes
    logging.info("Loading ZIP codes from zip_codes_2026.csv...")
    zip_df = pd.read_csv('zip_codes_2026.csv')

    # Load merged results to get state info
    logging.info("Loading state information from merged_results_v9.csv...")
    merged_df = pd.read_csv('merged_results_v9.csv')

    # Merge to get state for each ZIP
    zip_with_state = zip_df.merge(
        merged_df[['zip_code', 'state', 'rating_area']].drop_duplicates(),
        on='zip_code',
        how='left'
    )

    total_zips = len(zip_with_state)
    logging.info(f"Processing {total_zips} ZIP codes for age {AGE}...")

    results = []

    for index, row in zip_with_state.iterrows():
        zip_code = str(row['zip_code']).zfill(5)
        state = row['state']
        rating_area = row['rating_area']

        logging.info(f"[{index+1}/{total_zips}] Processing {zip_code} ({state}, Rating Area {rating_area})")

        try:
            result = scrape_kff_calculator(state, zip_code, AGE)
            results.append(result)
            logging.info(f"  → Success: ${result['Unsubsidized Cost']}")
        except Exception as e:
            logging.error(f"  → Failed: {str(e)}")
            results.append({
                "State": state,
                "Zip": zip_code,
                "Age": AGE,
                "Unsubsidized Cost": "ERROR",
            })

    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"slspc_results_2026_age{AGE}_{timestamp}.csv"

    result_df = pd.DataFrame(results)
    result_df.to_csv(output_file, index=False)

    logging.info(f"\n{'='*60}")
    logging.info(f"Scraping completed!")
    logging.info(f"Total ZIPs processed: {len(results)}")
    logging.info(f"Successful: {len([r for r in results if r['Unsubsidized Cost'] not in ['N/A', 'ERROR']])}")
    logging.info(f"Errors: {len([r for r in results if r['Unsubsidized Cost'] in ['N/A', 'ERROR']])}")
    logging.info(f"Results saved to: {output_file}")
    logging.info(f"{'='*60}")

if __name__ == "__main__":
    main()
