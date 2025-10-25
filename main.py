import asyncio
import aiosqlite
import re
import json
from aiogram import Bot, types
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from config import DB_NAME, BOT_TOKEN, CHANNEL_ID


def clean_html(text: str) -> str:
    """Remove unsupported HTML tags for Telegram."""
    if not text:
        return ""
    text = re.sub(r'</?p>', '\n', text)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<.*?>', '', text)
    return text.strip()


async def send_images(bot: Bot, chat_id: str, image_urls: list[str], caption: str):
    """Send one or multiple images and return list of message IDs."""
    if len(image_urls) == 1:
        msg = await bot.send_photo(chat_id=chat_id, photo=image_urls[0], caption=caption, parse_mode="HTML")
        return [msg.message_id]
    else:
        media = [types.InputMediaPhoto(media=image_urls[0], caption=caption, parse_mode="HTML")]
        for url in image_urls[1:]:
            media.append(types.InputMediaPhoto(media=url))
        messages = await bot.send_media_group(chat_id=chat_id, media=media)
        return [m.message_id for m in messages]


async def delete_previous_messages(bot: Bot, product_id: int):
    """Delete all Telegram messages for this product."""
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT message_id FROM product_messages WHERE product_id = ?", (product_id,)) as cur:
            rows = await cur.fetchall()

    if not rows:
        return

    for (msg_id,) in rows:
        try:
            await bot.delete_message(chat_id=CHANNEL_ID, message_id=msg_id)
            print(f"🗑️ Deleted message {msg_id}")
        except TelegramBadRequest:
            print(f"⚠️ Message {msg_id} could not be deleted (already removed).")

    # Clear DB records
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM product_messages WHERE product_id = ?", (product_id,))
        await db.commit()
        print(f"🧹 Cleared message IDs for product {product_id}.")


async def save_message_ids(product_id: int, message_ids: list[int]):
    """Save all message IDs for a product."""
    async with aiosqlite.connect(DB_NAME) as db:
        await db.executemany(
            "INSERT INTO product_messages (product_id, message_id) VALUES (?, ?)",
            [(product_id, mid) for mid in message_ids]
        )
        await db.commit()
        print(f"💾 Saved message IDs {message_ids} for product {product_id}.")


async def send_test_message():
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute(
            "SELECT id, name, description, url FROM products WHERE visible = 1 LIMIT 1"
        ) as cursor:
            product = await cursor.fetchone()
            if not product:
                print("No visible product found.")
                return

        product_id, name, description, url = product
        description = clean_html(description)

        async with db.execute(
            "SELECT image_url FROM product_images WHERE product_id = ?", (product_id,)
        ) as cursor:
            images = await cursor.fetchall()
            image_urls = [img[0] for img in images if img[0]]

    bot = Bot(token=BOT_TOKEN)

    try:
        # Step 1: Delete any previous messages for this product
        await delete_previous_messages(bot, product_id)

        # Step 2: Compose caption text
        caption = f"🛒 <b>{name}</b>\n\n{description}\n\n🔗 More info: {url}"

        # Step 3: Send images (or just caption if no images)
        message_ids = []
        if image_urls:
            try:
                message_ids = await send_images(bot, CHANNEL_ID, image_urls, caption)
            except TelegramRetryAfter as e:
                print(f"⚠️ Flood control hit. Retry after {e.timeout}s.")
                await asyncio.sleep(e.timeout)
                message_ids = await send_images(bot, CHANNEL_ID, image_urls, caption)
        else:
            msg = await bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode="HTML")
            message_ids = [msg.message_id]

        # Step 4: Save all sent message IDs
        if message_ids:
            await save_message_ids(product_id, message_ids)

        print("✅ Product post sent successfully.")

    finally:
        await bot.session.close()
        print("✅ Bot session closed safely.")


if __name__ == "__main__":
    asyncio.run(send_test_message())
