import requests
import certifi
from bs4 import BeautifulSoup
import re
import pandas as pd
import pygsheets
from datetime import datetime
from dotenv import load_dotenv
import os

# load env
load_dotenv()

SHEET_NAME = os.getenv("SHEET_NAME")

# connect google sheets
gc = pygsheets.authorize(service_file='credentials.json')
sh = gc.open(SHEET_NAME)

# open worksheet
wks = sh.worksheet_by_title("lender_rates")

# request webpage
url = "https://www.becu.org/rates/mortgage-rates"

response = requests.get(
    url,
    verify=certifi.where(),
    timeout=30,
    headers={
        "User-Agent": "Mozilla/5.0"
    }
)

response.raise_for_status()

# parse html
soup = BeautifulSoup(response.text, "lxml")

text = soup.get_text(separator="\n", strip=True)

# patterns
patterns = {
    "15Y Purchase": {
        "pattern": r"Fixed Rate 15 Year\s+([\d\.]+)",
        "loan_term": "15Y",
        "loan_purpose": "purchase"
    },
    "15Y Refinance": {
        "pattern": r"Fixed Rate Refinance 15 Year\s+([\d\.]+)",
        "loan_term": "15Y",
        "loan_purpose": "refinance"
    },
    "30Y Purchase": {
        "pattern": r"Fixed Rate 30 Year\s+([\d\.]+)",
        "loan_term": "30Y",
        "loan_purpose": "purchase"
    },
    "30Y Refinance": {
        "pattern": r"Fixed Rate Refinance 30 Year\s+([\d\.]+)",
        "loan_term": "30Y",
        "loan_purpose": "refinance"
    }
}

rows = []

for name, config in patterns.items():

    match = re.search(config["pattern"], text)

    if match:

        rate = float(match.group(1))

        rows.append([
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "Greater Seattle Area",
            "98033",
            "BECU",
            config["loan_purpose"],
            config["loan_term"],
            rate,
            "",
            "",
            url,
            95,
            "scraped from BECU mortgage rates page",
            match.group(0)
        ])

# create dataframe
df = pd.DataFrame(rows, columns=[
    "date",
    "collected_at",
    "region",
    "zip_code",
    "lender",
    "loan_purpose",
    "loan_term",
    "rate",
    "apr",
    "points",
    "source_url",
    "confidence_score",
    "notes",
    "raw_text"
])

# append rows
wks.append_table(
    values=df.values.tolist(),
    start="A1",
    dimension="ROWS",
    overwrite=False
)

print(df)
print(f"Inserted {len(df)} BECU lender rate rows.")