#!/usr/bin/env python3
"""
KFF Calculator Scraper - Version 2
Uses JavaScript event dispatching to trigger form validation
"""

from playwright.sync_api import sync_playwright
import pandas as pd
import re
import logging
import time

logging.basicConfig(level=logging.INFO, format='%(message)s')

def fill_field_with_events(page, selector, value, field_name):
    """Fill a field and trigger all the events a real user would trigger"""
    logging.info(f"  Filling {field_name}: {value}")

    page.evaluate("""
        ({selector, value}) => {
            const el = document.querySelector(selector);
            if (!el) throw new Error('Element not found: ' + selector);

            // Focus the element
            el.focus();

            // Set the value
            el.value = value;

            // Trigger all the events
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.dispatchEvent(new Event('blur', { bubbles: true }));
        }
    """, {"selector": selector, "value": value})
    page.wait_for_timeout(300)

def select_option_with_events(page, selector, value, field_name):
    """Select an option and trigger change events"""
    logging.info(f"  Selecting {field_name}: {value}")

    page.evaluate("""
        ({selector, value}) => {
            const el = document.querySelector(selector);
            if (!el) throw new Error('Element not found: ' + selector);

            el.focus();
            el.value = value;
            el.dispatchEvent(new Event('change', { bubbles: true }));
            el.dispatchEvent(new Event('blur', { bubbles: true }));
        }
    """, {"selector": selector, "value": value})
    page.wait_for_timeout(500)

def click_radio_with_events(page, selector, field_name):
    """Click a radio button with real events"""
    logging.info(f"  Clicking {field_name}")

    page.evaluate("""
        (selector) => {
            const el = document.querySelector(selector);
            if (!el) throw new Error('Element not found: ' + selector);

            el.focus();
            el.click();
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }
    """, selector)
    page.wait_for_timeout(300)

def scrape_kff_calculator(state, zip_code, age, headless=True):
    """Scrape KFF calculator for a single ZIP code"""

    logging.info(f"\n{'='*60}")
    logging.info(f"Scraping: {state.upper()} {zip_code} (age {age})")
    logging.info(f"{'='*60}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.set_default_timeout(30000)

        try:
            # 1. Load page
            logging.info("Step 1: Loading page...")
            page.goto("https://www.kff.org/interactive/calculator-aca-enhanced-premium-tax-credit/")
            page.wait_for_load_state("networkidle")

            # 2. Wait for form
            logging.info("Step 2: Waiting for form...")
            page.wait_for_selector("#subsidy-form", state="visible")

            # 3. Dismiss cookie banner
            logging.info("Step 3: Dismissing cookie banner...")
            page.wait_for_timeout(1000)
            for attempt in range(3):
                try:
                    ok_button = page.get_by_text("OK", exact=True)
                    if ok_button.is_visible():
                        ok_button.click(force=True)
                        page.wait_for_timeout(500)
                        logging.info("  ✓ Cookie banner dismissed")
                        break
                except:
                    pass
                try:
                    page.locator("#hs-eu-cookie-confirmation button").click(force=True)
                    page.wait_for_timeout(500)
                    logging.info("  ✓ Cookie banner dismissed")
                    break
                except:
                    pass

            # 4. Fill form with event triggering
            logging.info("Step 4: Filling form fields...")

            # State
            select_option_with_events(page, "#state-dd", state.lower(), "State")
            page.wait_for_load_state("networkidle")

            # ZIP code
            fill_field_with_events(page, "input[name='zip']", zip_code, "ZIP")

            # Income
            fill_field_with_events(page, "input[name='income']", "1000000", "Income")

            # Employer coverage (No)
            click_radio_with_events(page, "#employer-coverage-0", "Employer coverage: No")

            # Household size
            select_option_with_events(page, "#number-people", "1", "Household size")
            page.wait_for_timeout(1000)  # Wait for adult/child fields to appear

            # Handle age based on adult vs child
            if age <= 20:
                select_option_with_events(page, "#number-adults", "0", "Adults")
                select_option_with_events(page, "#number-children", "1", "Children")
                page.wait_for_timeout(500)
                select_option_with_events(page, "select[name='children[0][age]']", str(age), "Child age")
            else:
                select_option_with_events(page, "#number-adults", "1", "Adults")
                select_option_with_events(page, "#number-children", "0", "Children")
                page.wait_for_timeout(500)
                select_option_with_events(page, "select[name='adults[0][age]']", str(age), "Adult age")

            # 5. Wait for any async validation
            logging.info("Step 5: Waiting for validation...")
            page.wait_for_load_state("networkidle")
            page.wait_for_timeout(1000)

            # 6. Check submit button status
            logging.info("Step 6: Checking submit button...")
            submit_disabled = page.evaluate("""
                () => {
                    const btn = document.querySelector('input[type="submit"][value="Submit"]');
                    return btn ? btn.disabled : true;
                }
            """)

            logging.info(f"  Submit button disabled: {submit_disabled}")

            # 7. Submit the form
            logging.info("Step 7: Submitting form...")

            # First, try clicking if it's enabled
            if not submit_disabled:
                try:
                    page.locator("input[type='submit'][value='Submit']").click(timeout=5000)
                    logging.info("  ✓ Clicked submit button")
                except Exception as e:
                    logging.warning(f"  Click failed: {e}, trying JS submit...")
                    page.evaluate("document.querySelector('#subsidy-form').requestSubmit()")
            else:
                # Force submit via JavaScript
                logging.info("  Button disabled, forcing submit via JS...")
                page.evaluate("document.querySelector('#subsidy-form').requestSubmit()")

            # 8. Wait for results
            logging.info("Step 8: Waiting for results...")
            page.wait_for_selector("text=Your cost for a silver plan", state="visible", timeout=20000)
            logging.info("  ✓ Results loaded!")

            # 9. Extract data
            # Save HTML for debugging
            import os
            debug_dir = f"/tmp/debug_{zip_code}"
            os.makedirs(debug_dir, exist_ok=True)
            with open(f"{debug_dir}/results_page.html", "w") as f:
                f.write(page.content())
            logging.info(f"  Saved results HTML to {debug_dir}/results_page.html")

            cost = extract_unsubsidized_cost(page)
            logging.info(f"  → Unsubsidized cost: ${cost}")

            browser.close()

            return {
                "State": state.upper(),
                "Zip": zip_code,
                "Age": age,
                "Unsubsidized Cost": cost,
            }

        except Exception as e:
            logging.error(f"ERROR: {str(e)}")
            browser.close()
            return {
                "State": state.upper(),
                "Zip": zip_code,
                "Age": age,
                "Unsubsidized Cost": "ERROR",
            }

def extract_unsubsidized_cost(page):
    """Extract the unsubsidized silver plan cost from results"""

    logging.info("Extracting cost from results page...")

    # Strategy 1: Look for bold-blue span with dollar amount near "silver plan"
    try:
        # Get all bold-blue spans
        spans = page.locator("span.bold-blue").all()
        logging.info(f"  Found {len(spans)} bold-blue spans")

        for span in spans:
            text = span.inner_text()
            # Look for dollar amounts
            if text.startswith("$") and re.match(r"\$\d+", text):
                # Check if this is near "silver plan" text
                parent_text = span.evaluate("el => el.closest('dd').previousElementSibling.innerText")
                if "silver plan" in parent_text.lower():
                    cost = text.replace("$", "").replace(",", "")
                    logging.info(f"  Found silver plan cost: ${cost}")
                    return cost
    except Exception as e:
        logging.error(f"  Failed span search: {e}")

    # Strategy 2: Search full HTML for the pattern
    try:
        html = page.content()
        # Find: "silver plan would cost:</dt><dd><span class="bold-blue">$XXX</span>"
        match = re.search(r'silver plan would cost:.*?<span[^>]*>\$(\d+,?\d*)</span>', html, re.DOTALL | re.IGNORECASE)
        if match:
            cost = match.group(1).replace(",", "")
            logging.info(f"  Found cost in HTML: ${cost}")
            return cost
    except Exception as e:
        logging.error(f"  Failed HTML search: {e}")

    # Strategy 3: Just get the first bold-blue dollar amount
    try:
        spans = page.locator("span.bold-blue").all()
        for span in spans:
            text = span.inner_text()
            if text.startswith("$"):
                cost = text.replace("$", "").replace(",", "")
                logging.warning(f"  Using first dollar amount found: ${cost}")
                return cost
    except Exception as e:
        logging.error(f"  Failed fallback search: {e}")

    return "N/A"

def main():
    import sys
    import os

    if len(sys.argv) < 2:
        print("Usage: python scraper_v2.py <csv_file> [--visible]")
        print("Example: python scraper_v2.py zip_codes_test_5.csv")
        sys.exit(1)

    csv_file = sys.argv[1]
    headless = "--visible" not in sys.argv

    # Read ZIP codes
    df = pd.read_csv(csv_file)

    # Load state lookup from merged_results_v9.csv
    print("Loading state lookup from merged_results_v9.csv...")
    merged_df = pd.read_csv('merged_results_v9.csv')
    merged_df['zip_code'] = merged_df['zip_code'].astype(str).str.zfill(5)
    zip_to_state = merged_df.groupby('zip_code')['state'].first().to_dict()

    age = 0
    results = []
    total = len(df)

    print(f"\n{'='*60}")
    print(f"Starting scrape of {total} ZIP codes")
    print(f"Mode: {'HEADLESS' if headless else 'VISIBLE'}")
    print(f"{'='*60}\n")

    output_file = csv_file.replace('.csv', '_results.csv')

    # Check if results file exists (for resume)
    if os.path.exists(output_file):
        existing_df = pd.read_csv(output_file)
        existing_zips = set(existing_df['Zip'].astype(str).str.zfill(5))
        print(f"Found existing results file with {len(existing_zips)} ZIPs already processed")
        print(f"Resuming from where we left off...\n")
    else:
        existing_zips = set()

    for idx, row in df.iterrows():
        zip_code = str(row['zip_code']).zfill(5)

        # Skip if already processed
        if zip_code in existing_zips:
            print(f"[{idx+1}/{total}] Skipping {zip_code} (already processed)")
            continue

        # Get state from row if available, otherwise look it up
        if 'state' in row and pd.notna(row['state']):
            state = row['state']
        elif zip_code in zip_to_state:
            state = zip_to_state[zip_code]
        else:
            print(f"WARNING: Could not find state for ZIP {zip_code}, skipping...")
            continue

        print(f"\n[{idx+1}/{total}] Processing {state.upper()} {zip_code}...")

        result = scrape_kff_calculator(state, zip_code, age, headless=headless)
        results.append(result)

        # Save progress after every ZIP (incremental save)
        results_df = pd.DataFrame(results)
        if os.path.exists(output_file):
            # Append to existing
            existing_df = pd.read_csv(output_file)
            combined_df = pd.concat([existing_df, results_df], ignore_index=True)
            combined_df.to_csv(output_file, index=False)
        else:
            # Create new
            results_df.to_csv(output_file, index=False)

        results = []  # Clear for next iteration

        time.sleep(1)  # Be nice to the server

    # Final save (in case there are any remaining)
    if results:
        results_df = pd.DataFrame(results)
        if os.path.exists(output_file):
            existing_df = pd.read_csv(output_file)
            combined_df = pd.concat([existing_df, results_df], ignore_index=True)
            combined_df.to_csv(output_file, index=False)
        else:
            results_df.to_csv(output_file, index=False)

    print(f"\n{'='*60}")
    print(f"COMPLETE! Results saved to: {output_file}")
    print(f"{'='*60}\n")
    print(results_df)

if __name__ == "__main__":
    main()
