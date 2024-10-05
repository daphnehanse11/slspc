import streamlit as st
from playwright.sync_api import sync_playwright
import pandas as pd
import re
import logging

logging.basicConfig(level=logging.INFO)


def scrape_kff_calculator(state, zip_code, age):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.set_default_timeout(60000)  # Increase timeout to 60 seconds

        try:
            page.goto("https://www.kff.org/interactive/subsidy-calculator/")

            # Wait for the form to be visible
            page.wait_for_selector("#subsidy-form", state="visible")

            # Fill out the form
            page.select_option("#state-dd", state)
            page.fill("input[name='zip']", zip_code)
            page.fill(
                "input[name='income']", "1000000"
            )  # Use 1 million as income
            page.click("#employer-coverage-0")  # Assume no employer coverage
            page.select_option("#number-people", "1")  # 1-person household

            if state.upper() in ["NY", "VT"]:
                page.select_option("#number-people-alternate", "individual")
            else:
                if age >= 21:
                    page.select_option("#number-adults", "1")
                    page.select_option("#number-children", "0")
                    page.select_option(
                        "select[name='adults[0][age]']", str(age)
                    )
                else:
                    page.select_option("#number-adults", "0")
                    page.select_option("#number-children", "1")
                    page.select_option(
                        "select[name='children[0][age]']", str(age)
                    )

            # Submit the form
            page.click("input[type='submit'][value='Submit']")

            # Wait for results to load
            page.wait_for_selector(".results-list", state="visible")

            # Extract the data
            unsubsidized_cost = extract_unsubsidized_cost(page)

            browser.close()

            return {
                "State": state,
                "Zip": zip_code,
                "Age": age,
                "Unsubsidized Cost": unsubsidized_cost,
            }

        except Exception as e:
            logging.error(f"An error occurred while scraping: {str(e)}")
            browser.close()
            raise


def extract_unsubsidized_cost(page):
    try:
        cost_text = page.inner_text(
            "dt:has-text('Without financial help, your silver plan would cost:') + dd"
        )
        match = re.search(r"\$(\d+,?\d*)", cost_text)
        if match:
            return match.group(1)  # Return the cost as a string with comma
        else:
            return "N/A"
    except Exception as e:
        logging.error(f"Error extracting unsubsidized cost: {str(e)}")
        return "N/A"


def main():
    st.title("KFF Second Lowest Cost Silver Plan Scraper")

    st.sidebar.header("Input Parameters")
    state = st.sidebar.selectbox(
        "Select State",
        [
            "al",
            "ak",
            "az",
            "ar",
            "ca",
            "co",
            "ct",
            "de",
            "fl",
            "ga",
            "hi",
            "id",
            "il",
            "in",
            "ia",
            "ks",
            "ky",
            "la",
            "me",
            "md",
            "ma",
            "mi",
            "mn",
            "ms",
            "mo",
            "mt",
            "ne",
            "nv",
            "nh",
            "nj",
            "nm",
            "ny",
            "nc",
            "nd",
            "oh",
            "ok",
            "or",
            "pa",
            "ri",
            "sc",
            "sd",
            "tn",
            "tx",
            "ut",
            "vt",
            "va",
            "wa",
            "wv",
            "wi",
            "wy",
        ],
    )
    zip_code = st.sidebar.text_input("Enter ZIP Code", "80204")
    age = st.sidebar.number_input(
        "Age of applicant", min_value=0, max_value=64, value=30
    )

    if st.sidebar.button("Calculate Premium"):
        with st.spinner("Calculating premium... This may take a moment."):
            try:
                result = scrape_kff_calculator(state, zip_code, age)
                st.success("Calculation completed!")
                st.write(result)

                df = pd.DataFrame([result])
                csv = df.to_csv(index=False)
                st.download_button(
                    label="Download data as CSV",
                    data=csv,
                    file_name="kff_second_lowest_cost_silver_plan.csv",
                    mime="text/csv",
                )
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
                st.error(
                    "Please try again. If the problem persists, the website might be experiencing issues."
                )


if __name__ == "__main__":
    main()
