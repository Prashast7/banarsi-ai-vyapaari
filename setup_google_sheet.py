# setup_google_sheet.py
import gspread
from google.oauth2.service_account import Credentials

# Step 1: Set up credentials
creds = Credentials.from_service_account_file('credentials.json')

# Step 2: Authorize access
gc = gspread.authorize(creds)

# Step 3: Create a new spreadsheet
spreadsheet = gc.create('Banarsi_Sari_Sales')

# Step 4: Get the first worksheet
worksheet = spreadsheet.sheet1

# Step 5: Add header row
worksheet.append_row(['Phone', 'Sari Type', 'Design', 'Price', 'Timestamp'])

# Step 6: Print the URL for future reference
print(f"Google Sheet created successfully!")
print(f"Share this URL with your service account: {spreadsheet.url}")
print(f"Service account email: {creds.service_account_email}")
