import json
from openai import OpenAI
from scrape_wells_fargo_rates import scrape_wells_fargo, write_to_sheet
from dotenv import load_dotenv

load_dotenv()

client = OpenAI()

last_df = None


def run_wells_fargo_scraper():
    global last_df
    try:
        df = scrape_wells_fargo()
        last_df = df

        return {
            "status": "success",
            "row_count": len(df),
            "columns": list(df.columns),
            "preview": df.to_dict(orient="records"),
        }
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
        }


def validate_wells_fargo_result():
    global last_df

    issues = []

    if last_df is None:
        return {
            "status": "failed",
            "issues": ["No dataframe exists. Scraper has not run."]
        }

    if last_df.empty:
        issues.append("Scraper returned empty dataframe.")

    if len(last_df) != 4:
        issues.append(f"Expected 4 rows: purchase/refinance x 15Y/30Y. Got {len(last_df)} rows.")

    for _, row in last_df.iterrows():
        rate = float(row["rate"])
        apr = float(row["apr"])

        if rate < 3 or rate > 12:
            issues.append(f"Suspicious rate: {rate}")

        if apr < rate:
            issues.append(f"APR lower than rate: rate={rate}, apr={apr}")

    return {
        "status": "success" if not issues else "warning",
        "issues": issues,
    }


def write_current_result_to_sheet():
    global last_df

    if last_df is None or last_df.empty:
        return {
            "status": "failed",
            "message": "No valid dataframe to write."
        }

    write_to_sheet(last_df)

    return {
        "status": "success",
        "message": f"Inserted {len(last_df)} rows into Google Sheet."
    }


def send_notification(message):
    print("NOTIFICATION:", message)
    return {
        "status": "success",
        "message": message
    }

# 2. tool registry
TOOLS = {
    "run_wells_fargo_scraper": run_wells_fargo_scraper,
    "validate_wells_fargo_result": validate_wells_fargo_result,
    "write_current_result_to_sheet": write_current_result_to_sheet,
    "send_notification": send_notification,
}


# 3. tool definitions to OpenAI 
tool_definitions = [
    {
        "type": "function",
        "name": "run_wells_fargo_scraper",
        "description": "Run the local Playwright scraper for Wells Fargo mortgage rates.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "validate_wells_fargo_result",
        "description": "Validate whether the scraped Wells Fargo mortgage rate result looks complete and reasonable.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "write_current_result_to_sheet",
        "description": "Write the latest validated Wells Fargo mortgage rate dataframe to Google Sheet.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "type": "function",
        "name": "send_notification",
        "description": "Send a local notification message. For now this prints the message; later it can call Telegram.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string"}
            },
            "required": ["message"]
        }
    }
]

# 4. agent loop
def run_agent():
    conversation = [
        {
            "role": "user",
            "content": """
You are a local mortgage monitoring agent.

Goal:
1. Run the Wells Fargo mortgage rate scraper.
2. Validate whether the result is complete and reasonable.
3. If valid, write it to Google Sheet.
4. If invalid, decide whether to retry once or notify the user.
5. Send a final notification summarizing what happened.

Important:
- Do not write to Google Sheet unless validation is successful.
- Expected result is 4 rows: purchase 15Y, purchase 30Y, refinance 15Y, refinance 30Y.
- Rates should usually be between 3% and 12%.
- APR should not be lower than rate.
"""
        }
    ]

    max_steps = 8

    for step in range(max_steps):
        response = client.responses.create(
            model="gpt-5.2",
            input=conversation,
            tools=tool_definitions,
        )

        conversation += response.output

        tool_calls = [
            item for item in response.output
            if item.type == "function_call"
        ]

        if not tool_calls:
            print(response.output_text)
            return response.output_text

        for tool_call in tool_calls:
            tool_name = tool_call.name
            args = json.loads(tool_call.arguments or "{}")

            print(f"AI decided to call tool: {tool_name}")
            print(f"Arguments: {args}")

            tool_result = TOOLS[tool_name](**args)

            conversation.append({
                "type": "function_call_output",
                "call_id": tool_call.call_id,
                "output": json.dumps(tool_result),
            })

    return "Agent stopped because max_steps was reached."



if __name__ == "__main__":
    run_agent()