#!/usr/bin/env python3
import re
from bs4 import BeautifulSoup

def parse_cms_rating_areas(html_file, state):
    """Parse CMS rating area HTML files to extract county-to-rating-area mappings"""

    with open(html_file, 'r', encoding='utf-8') as f:
        html = f.read()

    soup = BeautifulSoup(html, 'html.parser')

    # Find all td elements with class xl65 (rating areas) and xl66 (counties)
    rating_area_cells = soup.find_all('td', class_='xl65')
    county_cells = soup.find_all('td', class_='xl66')

    results = []

    # Process county cells and match with rating areas
    for i, county_cell in enumerate(county_cells):
        county = county_cell.get_text(strip=True)

        # Skip header row
        if county == 'County' or not county:
            continue

        # Find the corresponding rating area (should be just before this county)
        # Look backwards through rating area cells
        rating_area = None
        for ra_cell in rating_area_cells:
            ra_text = ra_cell.get_text(strip=True)
            match = re.search(r'Rating Area (\d+[SN]?)', ra_text)
            if match:
                # Check if this rating area cell comes before our county cell in the document
                if ra_cell.sourceline and county_cell.sourceline:
                    if ra_cell.sourceline <= county_cell.sourceline:
                        rating_area = match.group(1)

        if not rating_area:
            # Try a simpler approach - just find the nearest rating area text before this county
            # Get all text before this point
            all_text = html[:html.find(str(county_cell))]
            matches = re.findall(r'Rating Area (\d+[SN]?)', all_text)
            if matches:
                rating_area = matches[-1]  # Get the last/most recent rating area

        if county and rating_area:
            results.append(f"{state},{rating_area},{county}")

    return results

# Parse Texas
print("Parsing Texas rating areas...")
tx_results = parse_cms_rating_areas('/tmp/tx_rating_areas.html', 'TX')
print(f"Found {len(tx_results)} Texas county mappings")
print("First 10 TX entries:")
for entry in tx_results[:10]:
    print(entry)

print("\n" + "="*50 + "\n")

# Parse Maine
print("Parsing Maine rating areas...")
me_results = parse_cms_rating_areas('/tmp/me_rating_areas.html', 'ME')
print(f"Found {len(me_results)} Maine county mappings")
print("All ME entries:")
for entry in me_results:
    print(entry)

# Save to files
with open('/tmp/tx_rating_areas_parsed.csv', 'w') as f:
    f.write("STATE,AREA,COUNTY_ZIP3\n")
    for entry in tx_results:
        f.write(entry + "\n")

with open('/tmp/me_rating_areas_parsed.csv', 'w') as f:
    f.write("STATE,AREA,COUNTY_ZIP3\n")
    for entry in me_results:
        f.write(entry + "\n")

print(f"\nSaved to /tmp/tx_rating_areas_parsed.csv and /tmp/me_rating_areas_parsed.csv")
