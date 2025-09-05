import os
from dotenv import load_dotenv
import requests
from datetime import datetime, timedelta
import pytz
import pyotp
import json
# import csv
from time import sleep
import re

# Only load .env when not running in GitHub Actions
if not os.getenv("GITHUB_ACTIONS"):
    load_dotenv()  # Loads local secrets from .env
else:
    print("Loaded from GitHub Actions")

url = os.getenv("URL", "")
print(f"URL LOADED: {bool(url)}")

client_id = os.getenv("CLIENT_ID", "")
print(f"Client ID LOADED: {bool(client_id)}")

api_key = os.getenv("API_KEY", "")
print(f"API KEY LOADED: {bool(api_key)}")

mpin = os.getenv("MPIN", "")
print(f"MPIN LOADED: {bool(mpin)}")

secret_key = os.getenv("SECRET_KEY", "")
print(f"SECRET_KEY LOADED: {bool(secret_key)}")

jwt_token = ""

url_1 = os.getenv("URL_1", "")
print(f"URL-1 LOADED: {bool(url_1)}")

url_2 = os.getenv("URL_2", "")
print(f"URL-2 LOADED: {bool(url_2)}")

previous_day = ""


HEADERS = {
    "Accept": "application/json",
    "X-UserType": "USER",
    "X-SourceID": "WEB",
    "X-ClientLocalIP": "127.0.0.1",
    "X-ClientPublicIP": "106.193.147.98",
    "X-MACAddress": "41:ca:37:aa:5d:07",
    "X-PrivateKey": api_key,
    "Content-Type": "application/json",
}

def ist_now():
    return datetime.now(pytz.timezone("Asia/Kolkata"))

def split_name(key=""):

    # Regex to extract components
    match = re.match(r"([A-Z]+)(\d{2})([A-Z]{3})(\d{2})(\d+)(CE|PE)", key)

    if match:
        symbol, day, month_str, year_suffix, strike, option_type = match.groups()

        # Convert to full date format
        month_map = {
            "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
            "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12
        }
        year_full = 2000 + int(year_suffix)
        month = month_map[month_str]
        date_obj = datetime(year_full, month, int(day))
        formatted_date = date_obj.strftime("%d-%b-%Y")

        return symbol, formatted_date, strike, option_type
    return ""




def get_data(item = {}, column_header = "",date2="", date1=""):

    token = list(item.keys())[0]

    payload = {
    "exchange": "NFO",
    "symboltoken": f"{token}",
    "interval": "ONE_DAY",
    "fromdate": f"{date1} 09:15",
    "todate": f"{date2} 15:30"
    }
    
    response = requests.request("POST", url=url_2, headers=HEADERS, data=json.dumps(payload))
    
    print(response.text)

    json_response = response.json()
    
    json_data = json_response['data'][0] if len(json_response['data']) else ["-","-","-","-","-",0]
    
    symbol, formatted_date, strike, option_type = split_name(item[token])
    option_type = "Call" if "CE" in option_type else "Put"

    print("---------------")

    return {

        f"{column_header}":f"{option_type}{strike}",
        "instrumentType":"Index Options",
        "expiryDate":f"{formatted_date}",
        "optionType":option_type,
        "strikePrice":strike,
        "openPrice":json_data[1],
        "highPrice":json_data[2],
        "lowPrice":json_data[3],
        "closePrice":json_data[4],
        "volume":json_data[5],
        "name":item[token],
        "token":token,
    }




def login_broker():
        # Generate TOTP
        totp = pyotp.TOTP(secret_key).now()
   
        # Login Request Payload
        payload = {
            "clientcode": client_id,
            "password": mpin,  
            "totp": totp
        }

        response = requests.post(url=url_1, json=payload, headers=HEADERS)
        data = response.json()

        if data.get("status") is True:
            tokens = data.get("data", {})
            return tokens.get("jwtToken", "")

    

def get_previous_day():
    # Get the current date
    current_date = ist_now()

    # Calculate the previous day
    # if not os.getenv("GITHUB_ACTIONS"):
    #     previous_day = current_date - timedelta(days=1)
    # else:
    #     previous_day = current_date
    previous_day = current_date - timedelta(days=1)

    day_previous_day = current_date - timedelta(days=2)

    previous_day_formatted = previous_day.strftime("%Y-%m-%d")

    day_previous_day_formatted = day_previous_day.strftime("%Y-%m-%d")

    return previous_day_formatted, day_previous_day_formatted

def get_tokens_for_next_expiry(data):
    today = ist_now().date()

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
        previous_day, day_previous_day = get_previous_day()
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

        print(f"Total instruments needed to be processed..{len(result_tokens)}")

        jwt_token = login_broker()
        HEADERS.update({"Authorization": f"Bearer {jwt_token}"})

        output_dump = []
        sleep(1)

        date_obj = datetime.strptime(previous_day, "%Y-%m-%d")
        column_header = date_obj.strftime("%d.%m.%Y")
        for item in result_tokens:
            print(f"Processing item: {item}")
            output_dump.append(get_data(item=item, column_header=column_header, date2=previous_day, date1=day_previous_day))
            sleep(2)

        sorted_data_desc = sorted(output_dump, key=lambda x: x['volume'], reverse=True)

        # field_names = [f"{column_header}", "instrumentType",	"expiryDate","optionType", "strikePrice","openPrice","highPrice","lowPrice","closePrice","volume","name","token"]

        # with open(f"{previous_day}.csv", mode="w+", newline="") as csv_out:
        #     writer = csv.DictWriter(csv_out, fieldnames=field_names)
        #     writer.writeheader()
        #     writer.writerows(sorted_data_desc)
        

        # Create folders if they don't exist
        folder = "nifty"
        os.makedirs(folder, exist_ok=True)

        file_path = os.path.join(folder, f"{previous_day}.json")

        with open(file_path, "w+") as f:
            json.dump(sorted_data_desc, f)

        print("File created at:", file_path)

    except requests.RequestException as e:
        print(f"Failed to fetch data: {e}")

if __name__ == "__main__":
    main()