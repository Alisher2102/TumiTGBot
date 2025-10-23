import json
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import InputMediaPhoto
from config import BOT_TOKEN, CHANNEL_ID

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


async def load_products():
    with open("products.json", "r", encoding="utf-8") as f:
        return json.load(f)


async def post_products():
    products = await load_products()
    for p in products:
        caption = f"**{p['name']}**\n💰 Цена: {p['price']}\n🔗 [Подробнее]({p['url']})"
        await bot.send_photo(chat_id=CHANNEL_ID, photo=p["image"], caption=caption, parse_mode="Markdown")
        await asyncio.sleep(3)  # задержка между постами, чтобы не словить flood limit


async def main():
    await post_products()


if __name__ == "__main__":
    asyncio.run(main())