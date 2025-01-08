import streamlit as st
from playwright.sync_api import sync_playwright
import pandas as pd
import re
import logging
import time
import random

logging.basicConfig(level=logging.INFO)

def scrape_kff_calculator(state, zip_code, age):
    """Scrapes the KFF subsidy calculator for a single (state, ZIP, age) and returns the unsubsidized cost."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60_000)

        try:
            page.goto("https://www.kff.org/interactive/subsidy-calculator/")
            
            # Wait for form and fill it out
            page.wait_for_selector("#subsidy-form", state="visible")
            page.select_option("#state-dd", state)
            page.fill("input[name='zip']", zip_code)
            
            # Wait for county selector to appear and become enabled
            page.wait_for_selector("select#county-dd:not([disabled])", timeout=10000)
            # Give it a moment to populate
            page.wait_for_timeout(1000)
            
            # Get available counties and select the first one
            counties = page.eval_on_selector_all('select#county-dd option:not([disabled])', 'elements => elements.map(e => e.value)')
            if counties and len(counties) > 1:  # Skip first empty option
                page.select_option("#county-dd", counties[1])
                
            page.fill("input[name='income']", "1000000")
            page.click("#employer-coverage-0")
            page.select_option("#number-people", "1")

            # Age handling
            if state.upper() in ["NY", "VT"]:
                page.select_option("#number-people-alternate", "individual")
            else:
                if age >= 21:
                    page.select_option("#number-adults", "1")
                    page.select_option("#number-children", "0")
                    page.select_option("select[name='adults[0][age]']", str(age))
                else:
                    page.select_option("#number-adults", "0")
                    page.select_option("#number-children", "1")
                    page.select_option("select[name='children[0][age]']", str(age))

            # DEBUG: Log form values before submission
            st.write(f"\nDEBUG for ZIP {zip_code}:")
            st.write("State selected:", page.evaluate('document.querySelector("#state-dd").value'))
            st.write("ZIP entered:", page.evaluate('document.querySelector("input[name=\'zip\']").value'))
            st.write("Income entered:", page.evaluate('document.querySelector("input[name=\'income\']").value'))
            
            # Submit and wait for results
            page.click("input[type='submit'][value='Submit']")
            
            # Wait for results and check for errors
            page.wait_for_selector(".results-list", state="visible")
            
            # Check for error messages
            error_messages = page.query_selector_all(".error-message, .alert-error")
            if error_messages:
                for msg in error_messages:
                    st.write(f"Error found: {msg.inner_text()}")
                    
            # Take screenshot for debugging
            page.screenshot(path=f"debug_{zip_code}.png")
            
            selector = "dt:has-text('Without financial help, your silver plan would cost:') + dd"
            page.wait_for_selector(selector, state="visible", timeout=30000)
            
            # DEBUG: Log the entire results section
            results_section = page.query_selector(".results-list")
            if results_section:
                st.write(f"Results section content: {results_section.inner_text()}")
            
            # Add extra wait to ensure cost is loaded
            page.wait_for_timeout(3000)
            
            # Get the cost
            cost_element = page.query_selector(selector)
            if cost_element:
                cost_text = cost_element.inner_text()
                st.write(f"Raw cost text for ZIP {zip_code}: {cost_text}")
                
                # Extract the monthly cost
                match = re.search(r"\$(\d+,?\d*)", cost_text)
                if match:
                    cost = match.group(1).replace(',', '')
                    cost = int(cost)
                    if cost > 0:
                        browser.close()
                        return cost
            
            browser.close()
            return 0

        except Exception as e:
            logging.error(f"Error scraping ZIP {zip_code}: {str(e)}")
            browser.close()
            return 0

def process_csv(df, state, age):
    """Process all ZIP codes in a DataFrame, with retry logic for failed attempts."""
    results = []
    total_rows = len(df)
    max_retries = 3
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    st.write(f"Starting to process {total_rows} ZIP codes...")
    
    # Create empty DataFrame with correct schema
    results_df = pd.DataFrame(columns=['State', 'ZIP', 'Age', 'Unsubsidized Cost'])
    
    for index, row in df.iterrows():
        zip_code = str(row['zip_code']).zfill(5)
        retry_count = 0
        cost = 0
        
        while retry_count < max_retries and cost == 0:
            if retry_count > 0:
                st.write(f"Retrying ZIP {zip_code} (Attempt {retry_count + 1}/{max_retries})")
                time.sleep(random.uniform(5, 8))
            
            cost = scrape_kff_calculator(state, zip_code, age)
            if cost == 0:
                retry_count += 1
                
        # Record the result as a new row in the DataFrame
        new_row = pd.DataFrame([{
            'State': state,
            'ZIP': zip_code,
            'Age': age,
            'Unsubsidized Cost': cost if cost > 0 else 0  # Always use numeric value
        }])
        
        results_df = pd.concat([results_df, new_row], ignore_index=True)
        
        # Update progress
        progress = (index + 1) / total_rows
        progress_bar.progress(progress)
        status_text.text(f"Processed {index + 1} of {total_rows} ZIP codes")
        
        # Show result
        if cost > 0:
            st.write(f"✅ ZIP {zip_code}: ${cost}")
        else:
            st.write(f"❌ ZIP {zip_code}: Failed after {max_retries} attempts")
        
        # Delay between ZIPs
        time.sleep(random.uniform(2, 4))
    
    st.write(f"Completed processing. Got {len(results_df)} results.")
    
    # Convert DataFrame to string representation for display
    display_df = results_df.copy()
    display_df['Unsubsidized Cost'] = display_df['Unsubsidized Cost'].apply(
        lambda x: f"${x}" if x > 0 else "Failed - $0"
    )
    
    st.write("Results DataFrame:")
    st.write(display_df)
    
    return results_df

def main():
    st.title("KFF Second Lowest Cost Silver Plan Scraper (with retry logic)")

    st.sidebar.header("Input Parameters")
    state = st.sidebar.selectbox(
        "Select State",
        [
            "al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga",
            "hi", "id", "il", "in", "ia", "ks", "ky", "la", "me", "md",
            "ma", "mi", "mn", "ms", "mo", "mt", "ne", "nv", "nh", "nj",
            "nm", "ny", "nc", "nd", "oh", "ok", "or", "pa", "ri", "sc",
            "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", "wi", "wy"
        ],
    )
    age = st.sidebar.number_input("Age of applicant", min_value=0, max_value=64, value=30)

    uploaded_file = st.file_uploader("Choose a CSV file with ZIP codes", type="csv")

    if uploaded_file is not None:
        df = pd.read_csv(uploaded_file)
        st.write("Uploaded CSV preview:")
        st.write(df.head())

        if st.button("Process CSV"):
            with st.spinner("Processing ZIP codes... This may take a while."):
                try:
                    result_df = process_csv(df, state, age)
                    st.success("Processing completed!")
                    st.write(result_df)

                    csv_data = result_df.to_csv(index=False)
                    st.download_button(
                        label="Download results as CSV",
                        data=csv_data,
                        file_name="kff_second_lowest_cost_silver_plan_results.csv",
                        mime="text/csv",
                    )
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.error(
                        "Please try again. If the problem persists, the website might be experiencing issues or throttling."
                    )

if __name__ == "__main__":
    main()