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
        # Set headless=False if you want to watch the browser. Slowing down helps debug.
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Increase default timeout to 60 seconds
        page.set_default_timeout(60_000)

        try:
            page.goto("https://www.kff.org/interactive/subsidy-calculator/")

            # Wait for the form to be visible
            page.wait_for_selector("#subsidy-form", state="visible")

            # Fill out the form
            page.select_option("#state-dd", state)
            page.fill("input[name='zip']", zip_code)
            # Use a very high income to ensure unsubsidized cost is shown
            page.fill("input[name='income']", "1000000")

            # Assume no employer coverage
            page.click("#employer-coverage-0")

            # 1-person household
            page.select_option("#number-people", "1")

            # Age checks
            if state.upper() in ["NY", "VT"]:
                # Some states require using #number-people-alternate for single enrollment
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

            # Submit the form
            page.click("input[type='submit'][value='Submit']")

            # Wait for the results section to appear
            page.wait_for_selector(".results-list", state="visible")

            # **Crucial**: wait specifically for the text you care about to appear
            page.wait_for_selector(
                "dt:has-text('Without financial help, your silver plan would cost:') + dd",
                timeout=60_000
            )

            # Optional: give the page a moment to render final numbers
            page.wait_for_timeout(2000)

            # Extract the data
            unsubsidized_cost = extract_unsubsidized_cost(page, zip_code)

            browser.close()

            return {
                "State": state,
                "Zip": zip_code,
                "Age": age,
                "Unsubsidized Cost": unsubsidized_cost,
            }

        except Exception as e:
            logging.error(f"An error occurred while scraping (ZIP={zip_code}): {str(e)}")
            browser.close()
            # Reraise so we see the error in Streamlit
            raise

def extract_unsubsidized_cost(page, zip_code):
    """Extract the 'Without financial help, your silver plan would cost:' text and parse out the dollar amount."""
    try:
        # Grab the text that appears next to the relevant dt
        cost_text = page.inner_text(
            "dt:has-text('Without financial help, your silver plan would cost:') + dd"
        )
        # Debug print
        print(f"DEBUG for ZIP {zip_code}: {cost_text}")

        match = re.search(r"\$(\d+,?\d*)", cost_text)
        if match:
            return match.group(1)  # Return the cost (e.g. "921" or "1,234")
        else:
            return "N/A"
    except Exception as e:
        logging.error(f"Error extracting unsubsidized cost (ZIP={zip_code}): {str(e)}")
        return "N/A"

def process_csv(df, state, age):
    """Process all ZIP codes in a DataFrame, scraping KFF for each one."""
    results = []
    total_rows = len(df)
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for index, row in df.iterrows():
        zip_code = str(row['zip_code']).zfill(5)  # Ensure 5-digit ZIP code
        try:
            # --- SCRAPE ---
            result = scrape_kff_calculator(state, zip_code, age)
            results.append(result)
        except Exception as e:
            st.error(f"Error processing ZIP code {zip_code}: {str(e)}")

        # Update progress
        progress = (index + 1) / total_rows
        progress_bar.progress(progress)
        status_text.text(f"Processed {index + 1} of {total_rows} ZIP codes")

        # **Add a random delay** to reduce rate-limiting or server load
        time.sleep(random.uniform(2, 5))

    return pd.DataFrame(results)

def main():
    st.title("KFF Second Lowest Cost Silver Plan Scraper (app2)")

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
