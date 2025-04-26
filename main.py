import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta

# Only load .env when not running in GitHub Actions
if not os.getenv("GITHUB_ACTIONS"):
    load_dotenv()  # Loads local secrets from .env

url = os.getenv("URL", "")

def get_previous_day():
    # Get the current date
    current_date = datetime.now()

    # Calculate the previous day
    previous_day = current_date - timedelta(days=1)

    previous_day_formatted = previous_day.strftime("%Y-%m-%d")

    return previous_day_formatted

def get_tokens_for_next_expiry(data):
    today = datetime.now().date()

    # Step 1: Extract and sort unique expiry dates
    expiries = []
    for item in data:
        expiry_str = item['expiry']
        expiry_date = datetime.strptime(expiry_str, "%d%b%Y").date()
        expiries.append(expiry_date)
    
    expiries = sorted(set(expiries))

    # Step 2: Find the next valid expiry date
    next_expiry = None
    for expiry in expiries:
        if today <= expiry:
            next_expiry = expiry
            break

    if not next_expiry:
        print("No Valid Expiry Date found")
        return []  # No valid expiry found

    # Step 3: Get all tokens matching the valid expiry
    next_expiry_str = next_expiry.strftime("%d%b%Y").upper()
    print(f"Recent Expiry is...{next_expiry_str}")
    tokens = [{item['token']:item['symbol']} for item in data if item['expiry'].upper() == next_expiry_str]

    return tokens

def main():


    try:
        previous_day = get_previous_day()
        print(f"Getting data for .. {previous_day}")

        response = requests.get(url, stream=True)  # Stream response to avoid memory overload
        response.raise_for_status()
        data = response.json()


        instruments = [
            {
                "token":item["token"],
                "symbol":item["symbol"],
                "name":item["name"],
                "expiry":item.get("expiry", ""),
                "strike":str(item["strike"]),
                "lot_size":str(item["lotsize"]),
                "instrument_type":item["instrumenttype"],
                "exch_seg":item["exch_seg"]
            }
            for item in data
        ]

        index_options = list(filter(lambda opt: opt["exch_seg"] == "NFO" and opt["instrument_type"] == "OPTIDX" and opt["name"] == "NIFTY", instruments))

        result_tokens = get_tokens_for_next_expiry(index_options)

        print(f"Total instruments need to be processed..{len(result_tokens)}")

        for item in result_tokens:
            print(f"Processing item: {item}")
        


    except requests.RequestException as e:
        print(f"Failed to fetch data: {e}")

if __name__ == "__main__":
    main()