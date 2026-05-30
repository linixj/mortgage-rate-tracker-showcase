import pandas as pd
import pygsheets
from dotenv import load_dotenv
import os
from datetime import datetime, timedelta
import requests
import certifi
from io import StringIO
import time

load_dotenv()

SHEET_NAME = os.getenv("SHEET_NAME")

gc = pygsheets.authorize(service_file="credentials.json")
sh = gc.open(SHEET_NAME)
wks = sh.worksheet_by_title("benchmark_rates")

series_map = {
    "MORTGAGE30US": {
        "source": "Freddie Mac",
        "loan_term": "30Y",
        "loan_purpose": "purchase"
    },
    "MORTGAGE15US": {
        "source": "Freddie Mac",
        "loan_term": "15Y",
        "loan_purpose": "purchase"
    },
    "DGS10": {
        "source": "Treasury",
        "loan_term": "10Y",
        "loan_purpose": "market"
    }
}

start_date = datetime.today() - timedelta(days=180)
rows = []

def get_fred_csv(series_id):
    url = f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={series_id}"

    last_error = None

    for attempt in range(5):

        try:
            response = requests.get(
                url,
                verify=certifi.where(),
                timeout=60
            )

            response.raise_for_status()

            df = pd.read_csv(StringIO(response.text))
            df.columns = ["date", "value"]

            df["date"] = pd.to_datetime(df["date"])
            df = df[df["date"] >= start_date]

            df = df[df["value"] != "."]
            df["value"] = pd.to_numeric(df["value"], errors="coerce")
            df = df.dropna(subset=["value"])

            return df

        except requests.exceptions.RequestException as e:
            last_error = e

            print(
                f"FRED request failed for {series_id}, "
                f"attempt {attempt + 1}/3"
            )

            print(e)

            time.sleep(20)

    raise last_error

for series_id, meta in series_map.items():
    data = get_fred_csv(series_id)

    for _, row in data.iterrows():
        rows.append([
            row["date"].strftime("%Y-%m-%d"),
            "Greater Seattle Area",
            meta["source"],
            series_id,
            meta["loan_purpose"],
            meta["loan_term"],
            float(row["value"]),
            f"https://fred.stlouisfed.org/series/{series_id}",
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "historical backfill from FRED CSV"
        ])

df = pd.DataFrame(rows, columns=[
    "date",
    "region",
    "source",
    "series_id",
    "loan_purpose",
    "loan_term",
    "rate",
    "source_url",
    "last_updated",
    "notes"
])

wks.clear(start="A2")
wks.set_dataframe(df, (2, 1),copy_head=False)

print(f"Uploaded {len(df)} benchmark rows successfully.")