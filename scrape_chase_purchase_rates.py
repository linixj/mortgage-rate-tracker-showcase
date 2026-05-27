from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError
import re
import pandas as pd
from datetime import datetime
import pygsheets
from dotenv import load_dotenv
import os

load_dotenv()

URL = "https://www.chase.com/personal/mortgage/mortgage-rates"
ZIP_CODE = os.getenv("ZIP_CODE", "98101")
SHEET_NAME = os.getenv("SHEET_NAME", "Greater Seattle Mortgage Rate Tracker")

COLUMNS = [
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
    "raw_text",
]

def get_chase_purchase_text():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)

        zip_box = page.get_by_placeholder("Please enter 5 digit zip code")
        zip_box.wait_for(state="visible", timeout=30000)
        zip_box.click()

        # 比 fill 稳：模拟真实键盘输入
        page.keyboard.press("Meta+A")
        page.keyboard.type(ZIP_CODE, delay=100)

        page.wait_for_timeout(1000)
        print("ZIP VALUE:", zip_box.input_value())

        # page.get_by_role("button", name="See rates").click()
        # page.wait_for_timeout(1000)

        # GitHub headless 环境下，Chase purchase 有时 click 没触发提交，补一次 Enter
        # page.keyboard.press("Enter")
        zip_box.press("Enter")
        page.wait_for_timeout(20000)

        text = page.locator("body").inner_text()
        # print(text[:5000])

        # input("Press Enter to close browser...")
        browser.close()

        return text

def parse_chase_purchase_rates(text):
    patterns = {
        "30Y Purchase": {
            "pattern": r"30 year Fixed\s+([\d\.]+)%\s+([\d\.]+)%",
            "loan_term": "30Y",
            "loan_purpose": "purchase",
        },
        "15Y Purchase": {
            "pattern": r"15 year Fixed\s+([\d\.]+)%\s+([\d\.]+)%",
            "loan_term": "15Y",
            "loan_purpose": "purchase",
        },
    }

    rows = []

    for name, config in patterns.items():
        match = re.search(config["pattern"], text)

        if match:
            rate = float(match.group(1))
            apr = float(match.group(2))

            print("MATCHED:", name, match.group(0))

            rows.append([
                datetime.now().strftime("%Y-%m-%d"),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Greater Seattle Area",
                ZIP_CODE,
                "Chase",
                config["loan_purpose"],
                config["loan_term"],
                rate,
                apr,
                "approximately 1 point",
                URL,
                85,
                "Playwright scrape from Chase purchase rates page; rates based on Chase assumptions",
                match.group(0),
            ])
        else:
            print("NOT FOUND:", name)

    return pd.DataFrame(rows, columns=COLUMNS)

def write_to_sheet(df):
    if df.empty:
        print("No Chase purchase rates found. Nothing inserted.")
        return

    df = df.astype(str)

    gc = pygsheets.authorize(service_file="credentials.json")
    sh = gc.open(SHEET_NAME)
    wks = sh.worksheet_by_title("lender_rates")

    wks.append_table(
        values=df.values.tolist(),
        start="A1",
        end=None,
        dimension="ROWS",
        overwrite=False,
    )

    print(f"Inserted {len(df)} Chase purchase rows.")

try:
    text = get_chase_purchase_text()

    # print("DEBUG TABLE TEXT:")
    # start = text.find("LOAN TYPE")
    # end = text.find("The annual percentage rate")
    # print(text[start:end])
    print("DEBUG FULL TEXT:")
    print(text[:8000])

    df = parse_chase_purchase_rates(text)
    print(df)

    write_to_sheet(df)

except PlaywrightTimeoutError as e:
    print("Playwright timeout. Chase page did not finish loading the rate table.")
    print(e)