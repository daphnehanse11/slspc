import streamlit as st
from playwright.sync_api import sync_playwright
import pandas as pd
import re
import logging
from io import StringIO

logging.basicConfig(level=logging.INFO)

def extract_unsubsidized_cost(page):
    try:
        cost_text = page.inner_text(
            "dt:has-text('Without financial help, your silver plan would cost:') + dd"
        )
        match = re.search(r"\$(\d+,?\d*)", cost_text)
        if match:
            return match.group(1)
        else:
            return "N/A"
    except Exception as e:
        logging.error(f"Error extracting unsubsidized cost: {str(e)}")
        return "N/A"

def scrape_kff_calculator(state, zip_code, age):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60000)

        try:
            page.goto("https://www.kff.org/interactive/subsidy-calculator/")
            page.wait_for_selector("#subsidy-form", state="visible")

            # Enter state first
            page.select_option("#state-dd", state)
            logging.info(f"Selected state: {state}")
            
            # Enter ZIP and wait for county wrapper to become visible
            logging.info(f"Entering ZIP code: {zip_code}")
            page.fill("input[name='zip']", zip_code)
            page.wait_for_timeout(2000)  # Wait for AJAX

            try:
                # Wait for county wrapper to become visible
                logging.info("Checking for county dropdown...")
                page.wait_for_selector("#county-wrapper[style*='display: block']", timeout=5000)
                
                # Get list of counties
                counties = page.eval_on_selector_all("select[name='locale'] option", 
                    "options => options.map(opt => opt.textContent)")
                has_multiple_counties = len(counties) > 1
                logging.info(f"Found counties: {counties}")
                
            except Exception as e:
                logging.info("No county selection needed")
                has_multiple_counties = False
                counties = []

            results = []
            
            if has_multiple_counties and counties:
                # Handle multiple counties
                for county in counties:
                    logging.info(f"Processing county: {county}")
                    try:
                        # Select county
                        page.select_option("select[name='locale']", county)
                        logging.info(f"Selected county: {county}")
                        
                        # Fill out form
                        page.fill("input[name='income']", "1000000")
                        page.click("#employer-coverage-0")
                        page.select_option("#number-people", "1")

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

                        # Submit and get results
                        page.click("input[type='submit'][value='Submit']")
                        page.wait_for_selector(".results-list", state="visible")
                        unsubsidized_cost = extract_unsubsidized_cost(page)
                        
                        results.append({
                            "State": state,
                            "Zip": zip_code,
                            "County": county,
                            "Age": age,
                            "Unsubsidized Cost": unsubsidized_cost,
                        })
                        
                        # Reset for next county
                        page.goto("https://www.kff.org/interactive/subsidy-calculator/")
                        page.wait_for_selector("#subsidy-form", state="visible")
                        page.select_option("#state-dd", state)
                        page.fill("input[name='zip']", zip_code)
                        page.wait_for_timeout(2000)
                        
                    except Exception as e:
                        logging.error(f"Error processing county {county}: {str(e)}")
                        continue
            else:
                # Handle single county case
                page.fill("input[name='income']", "1000000")
                page.click("#employer-coverage-0")
                page.select_option("#number-people", "1")

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

                page.click("input[type='submit'][value='Submit']")
                page.wait_for_selector(".results-list", state="visible")
                unsubsidized_cost = extract_unsubsidized_cost(page)
                
                results.append({
                    "State": state,
                    "Zip": zip_code,
                    "County": None,
                    "Age": age,
                    "Unsubsidized Cost": unsubsidized_cost,
                })

            browser.close()
            return results

        except Exception as e:
            logging.error(f"An error occurred while scraping: {str(e)}")
            browser.close()
            raise

def process_csv(df, state, age):
    all_results = []
    total_rows = len(df)
    
    progress_bar = st.progress(0)
    status_text = st.empty()

    for index, row in df.iterrows():
        zip_code = str(row['zip_code']).zfill(5)
        try:
            results = scrape_kff_calculator(state, zip_code, age)
            all_results.extend(results)
        except Exception as e:
            st.error(f"Error processing ZIP code {zip_code}: {str(e)}")
        
        progress = (index + 1) / total_rows
        progress_bar.progress(progress)
        status_text.text(f"Processed {index + 1} of {total_rows} ZIP codes")

    return pd.DataFrame(all_results)

def main():
    st.title("KFF Second Lowest Cost Silver Plan Scraper")

    st.sidebar.header("Input Parameters")
    state = st.sidebar.selectbox(
        "Select State",
        ["al", "ak", "az", "ar", "ca", "co", "ct", "de", "fl", "ga", "hi", "id", 
         "il", "in", "ia", "ks", "ky", "la", "me", "md", "ma", "mi", "mn", "ms", 
         "mo", "mt", "ne", "nv", "nh", "nj", "nm", "ny", "nc", "nd", "oh", "ok", 
         "or", "pa", "ri", "sc", "sd", "tn", "tx", "ut", "vt", "va", "wa", "wv", 
         "wi", "wy"],
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

                    csv = result_df.to_csv(index=False)
                    st.download_button(
                        label="Download results as CSV",
                        data=csv,
                        file_name="kff_second_lowest_cost_silver_plan_results.csv",
                        mime="text/csv",
                    )
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")
                    st.error(
                        "Please try again. If the problem persists, the website might be experiencing issues."
                    )

if __name__ == "__main__":
    main()