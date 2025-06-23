from fastapi import FastAPI, Request, Form
from twilio.rest import Client
import os
import gspread
from google.oauth2.service_account import Credentials
import re
from datetime import datetime
import groq
import pandas as pd
from prophet import Prophet

app = FastAPI()

# Load environment variables
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GOOGLE_CREDS = os.getenv('GOOGLE_CREDS_FILE', 'credentials.json')

# Initialize Twilio client
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Initialize Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
creds = Credentials.from_service_account_file(GOOGLE_CREDS, scopes=SCOPES)
gc = gspread.authorize(creds)

# Initialize Groq/Llama3
groq_client = groq.Groq(api_key=GROQ_API_KEY)

def log_sale(msg: str, phone: str):
    """Log sale to Google Sheets"""
    try:
        # Extract sale details (format: #sale <type> <design> <price>)
        match = re.search(r"#sale\s+(\w+)\s+(\w+)\s+₹?(\d+)", msg)
        if not match:
            return "Invalid sale format. Use: #sale <type> <design> <price>"
        
        sari_type, design, price = match.groups()
        sheet = gc.open("Banarsi_Sari_Sales").sheet1
        sheet.append_row([phone, sari_type, design, int(price), datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
        return "Sale logged successfully! धन्यवाद 🙏"
    except Exception as e:
        return f"Error logging sale: {str(e)}"

def get_sari_response(query: str):
    """Get response from LLM about saris"""
    try:
        response = groq_client.chat.completions.create(
            model="llama3-8b-8192",
            messages=[
                {
                    "role": "system",
                    "content": "You are BanarsiBot - an expert on Banarasi saris from Varanasi. "
                               "You know about Katan, Organza, Georgette, Jangla, Butidar, etc. "
                               "Respond in a mix of Hindi and English (Hinglish) like a local shopkeeper. "
                               "Use terms like 'जी' and 'धन्यवाद'. Be helpful and polite."
                },
                {
                    "role": "user",
                    "content": query
                }
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}. Please try again later."

def predict_demand(shop_id: str):
    """Predict sari demand using Prophet"""
    try:
        sheet = gc.open("Banarsi_Sari_Sales").sheet1
        records = sheet.get_all_records()
        df = pd.DataFrame(records)
        
        # Prepare data for Prophet
        df['ds'] = pd.to_datetime(df['Timestamp'])
        df['y'] = df['Quantity'] if 'Quantity' in df.columns else 1
        
        # Group by date
        daily_sales = df.groupby('ds').size().reset_index(name='y')
        
        model = Prophet()
        model.fit(daily_sales)
        
        future = model.make_future_dataframe(periods=30)
        forecast = model.predict(future)
        
        return forecast[['ds', 'yhat', 'yhat_lower', 'yhat_upper']].tail(30)
    except Exception as e:
        return f"Prediction error: {str(e)}"

@app.post("/whatsapp")
async def whatsapp_webhook(
    From: str = Form(...),
    Body: str = Form(...)
):
    if "#sale" in Body:
        response = log_sale(Body, From)
    else:
        response = get_sari_response(Body)
    
    # Send WhatsApp reply
    twilio_client.messages.create(
        body=response,
        from_="whatsapp:+14155238886",  # Twilio sandbox number
        to=From
    )
    
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
