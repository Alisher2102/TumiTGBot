from dotenv import load_dotenv 
import os

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")
DB_NAME = os.getenv("DB_NAME", "products.db")  # fallback just in case
EXCEL_FILE = os.getenv("EXCEL_FILE")