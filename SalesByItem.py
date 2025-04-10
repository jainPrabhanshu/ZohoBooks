import requests
import pandas as pd
import time
import os
from datetime import datetime, date
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

# ========= CONFIG =========
load_dotenv(dotenv_path="credentials.env")

API_ENDPOINT = "https://www.zohoapis.in/books/v3/reports/salesbyitem"
ORGANIZATION_IDS = [
    {"id": "60014866712", "name": "EcomMasters"},
    {"id": "60020954651", "name": "EBRPL"}
]  # Add your org IDs here
SERVICE_ACCOUNT_FILE = 'credentials.json'

ACCESS_TOKEN = os.getenv("ZOHO_ACCESS_TOKEN")

# ========= FETCH ZOHO SALES DATA =========

def fetch_zoho_sales_data(access_token, organization_id, from_date, to_date,first_day_of_month,org_name):
    params = {
        "page": 1,
        "per_page": 200,
        "usestate": "true",
        "show_sub_categories": "false",
        "response_option": 1,
        "organization_id": organization_id,
        "from_date": from_date,
        "to_date": to_date,
        "filter_by": "TransactionDate.CustomDate"
    }

    headers = {
        'Authorization': f'Zoho-oauthtoken {access_token}'
    }

    response = requests.get(API_ENDPOINT, headers=headers, params=params)

    if response.status_code != 200:
        print(f"HTTP Error {response.status_code}: {response.text}")
        return []

    data = response.json()
    if not data.get("sales"):
        print("No sales data returned.")
        return []

    sales_list = data["sales"]
    records = []

    for sale in sales_list:
        item = sale.get("item", {})
        branch = sale.get("branch", {})

        record = {
            "Date": first_day_of_month.strftime('%Y-%m-%d'),
            "Organization":org_name,
            "Item_id": sale.get("item_id", ""),
            "Item_name": sale.get("item_name", ""),
            "Unit": sale.get("unit", ""),
            "Is_combo_product": sale.get("is_combo_product", ""),
            "Quantity_sold": sale.get("quantity_sold", ""),
            "Amount": sale.get("amount", ""),
            "Average_price": sale.get("average_price", ""),
            "Sku": item.get("sku", ""),
            "Branch_name": branch.get("branch_name", "")
        }
        records.append(record)

    return records

# ========= PROCESS & FLATTEN =========
def process_sales_data(sales_data):
    return pd.DataFrame(sales_data) if sales_data else pd.DataFrame()

def flatten(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    elif isinstance(value, dict):
        return ", ".join(f"{k}: {v}" for k, v in value.items())
    elif value is None:
        return ""
    return str(value)

# ========= GOOGLE SHEETS =========
def read_existing_sheet(service, spreadsheet_id, range_name):
    try:
        result = service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range=range_name
        ).execute()
        values = result.get('values', [])
        if not values:
            return pd.DataFrame()
        headers = values[0]
        data = values[1:]
        return pd.DataFrame(data, columns=headers)
    except Exception as e:
        print(f"Failed to read existing sheet: {e}")
        return pd.DataFrame()

def save_sales_to_gsheet(sales_df, spreadsheet_id, range_name="Sheet3!A1"):
    try:
        SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        service = build('sheets', 'v4', credentials=credentials)

        existing_df = read_existing_sheet(service, spreadsheet_id, range_name)

        # Remove current month data
        today = date.today()
        current_month = today.strftime('%Y-%m')
        # if not existing_df.empty and 'transaction_date' in existing_df.columns:
        #     existing_df = existing_df[~existing_df['transaction_date'].str.startswith(current_month)]

        combined_df = pd.concat([existing_df, sales_df], ignore_index=True)
        # combined_df.sort_values(by='transaction_date', inplace=True)

        values = [combined_df.columns.tolist()] + [
            [flatten(cell) for cell in row] for row in combined_df.values.tolist()
        ]

        service.spreadsheets().values().clear(
            spreadsheetId=spreadsheet_id, range=range_name
        ).execute()

        service.spreadsheets().values().update(
            spreadsheetId=spreadsheet_id,
            range=range_name,
            valueInputOption='RAW',
            body={'values': values}
        ).execute()

        print("Google Sheet updated successfully.")
        return True

    except Exception as e:
        print(f"❌ Google Sheets error: {e}")
        return False

# ========= MAIN =========
def main():
    today = date.today()
    first_day_of_month = today.replace(day=1)

    from_date = first_day_of_month.strftime('%Y-%m-%d')
    to_date = today.strftime('%Y-%m-%d')

    print(f"Fetching MTD data from {from_date} to {to_date}...")

    all_sales_data = []
    for org in ORGANIZATION_IDS:
        print(f"Fetching for {org['name']}...")
        org_sales = fetch_zoho_sales_data(ACCESS_TOKEN,org['id'],from_date,to_date,first_day_of_month,org['name'])
        all_sales_data.extend(org_sales)
        print(f"Records fetched: {len(org_sales)}")

    df = process_sales_data(all_sales_data)
    if df.empty:
        print("No sales data found for the selected date range. Sheet will not be updated.")
        return

    spreadsheet_id = '1DoESCx5MV-mz7T7uHftb-dSbs5d1IFbePdTCeY_fcL4'  # Replace with your actual sheet ID
    save_sales_to_gsheet(df, spreadsheet_id)

if __name__ == "__main__":
    main()
