# TumiTGBot

An asynchronous Telegram bot that synchronises an e-commerce product catalogue
to a Telegram channel. Built for automating product listings: it imports data
from Excel, posts product cards with image galleries to a channel, and keeps
those posts in sync as products are updated or removed.

## Features

- **Excel → database import** — reads a product spreadsheet (pandas) and loads
  it into SQLite, including multiple images per product.
- **Automated channel posting** — publishes product cards with single images or
  multi-image media groups, with HTML-formatted captions.
- **Post lifecycle management** — tracks Telegram message IDs per product so
  posts can be edited or deleted when the catalogue changes.
- **Flood-control handling** — retries with backoff on Telegram rate limits
  (`TelegramRetryAfter`), with configurable concurrency and delays.
- **Rotating file logging** — separate bot and error logs with size-based
  rotation.

## Tech Stack

- Python (asyncio)
- [aiogram](https://docs.aiogram.dev/) — Telegram Bot API framework
- aiosqlite — async SQLite access
- pandas — Excel import

## Getting Started

1. Clone the repo and install dependencies:
   ```bash
   pip install aiogram aiosqlite pandas openpyxl python-dotenv
Create a .env file:
BOT_TOKEN=your_telegram_bot_token
CHANNEL_ID=@your_channel
DB_NAME=products.db
EXCEL_FILE=products.xlsx
Initialise the database tables:
   ```bash
   python init_message_table.py
```
Import product data from Excel:
  ```bash
    python import_data.py
```
Run the bot:
  ```bash
    python main.py
