# import asyncio
# import aiosqlite
# import re
# from aiogram import Bot, types
# from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
# from config import DB_NAME, BOT_TOKEN, CHANNEL_ID


# def clean_html(text: str) -> str:
#     """Remove unsupported HTML tags for Telegram."""
#     if not text:
#         return ""
#     text = re.sub(r'</?p>', '\n', text)
#     text = re.sub(r'<br\s*/?>', '\n', text)
#     text = re.sub(r'<.*?>', '', text)
#     return text.strip()


# async def send_images(bot: Bot, chat_id: str, image_urls: list[str], caption: str):
#     """Send one or multiple images and return list of message IDs."""
#     if len(image_urls) == 1:
#         msg = await bot.send_photo(chat_id=chat_id, photo=image_urls[0], caption=caption, parse_mode="HTML")
#         return [msg.message_id]
#     else:
#         media = [types.InputMediaPhoto(media=image_urls[0], caption=caption, parse_mode="HTML")]
#         for url in image_urls[1:]:
#             media.append(types.InputMediaPhoto(media=url))
#         messages = await bot.send_media_group(chat_id=chat_id, media=media)
#         return [m.message_id for m in messages]


# async def delete_previous_messages(bot: Bot, product_id: int):
#     """Delete all Telegram messages for this product."""
#     async with aiosqlite.connect(DB_NAME) as db:
#         async with db.execute("SELECT message_id FROM product_messages WHERE product_id = ?", (product_id,)) as cur:
#             rows = await cur.fetchall()

#     if not rows:
#         return

#     for (msg_id,) in rows:
#         try:
#             await bot.delete_message(chat_id=CHANNEL_ID, message_id=msg_id)
#             print(f"🗑️ Deleted message {msg_id}")
#         except TelegramBadRequest:
#             print(f"⚠️ Message {msg_id} could not be deleted (already removed).")

#     # Clear DB records
#     async with aiosqlite.connect(DB_NAME) as db:
#         await db.execute("DELETE FROM product_messages WHERE product_id = ?", (product_id,))
#         await db.commit()
#         print(f"🧹 Cleared message IDs for product {product_id}.")


# async def save_message_ids(product_id: int, message_ids: list[int]):
#     """Save all message IDs for a product."""
#     async with aiosqlite.connect(DB_NAME) as db:
#         await db.executemany(
#             "INSERT INTO product_messages (product_id, message_id) VALUES (?, ?)",
#             [(product_id, mid) for mid in message_ids]
#         )
#         await db.commit()
#         print(f"💾 Saved message IDs {message_ids} for product {product_id}.")


# async def send_test_message():
#     async with aiosqlite.connect(DB_NAME) as db:
#         async with db.execute(
#             "SELECT id, name, description, url FROM products WHERE visible = 1 LIMIT 1"
#         ) as cursor:
#             product = await cursor.fetchone()
#             if not product:
#                 print("No visible product found.")
#                 return

#         product_id, name, description, url = product
#         description = clean_html(description)

#         async with db.execute(
#             "SELECT image_url FROM product_images WHERE product_id = ?", (product_id,)
#         ) as cursor:
#             images = await cursor.fetchall()
#             image_urls = [img[0] for img in images if img[0]]

#     bot = Bot(token=BOT_TOKEN)

#     try:
#         # Step 1: Delete any previous messages for this product
#         await delete_previous_messages(bot, product_id)

#         # Step 2: Compose caption text
#         caption = f"🛒 <b>{name}</b>\n\n{description}\n\n🔗 More info: {url}"

#         # Step 3: Send images (or just caption if no images)
#         message_ids = []
#         if image_urls:
#             try:
#                 message_ids = await send_images(bot, CHANNEL_ID, image_urls, caption)
#             except TelegramRetryAfter as e:
#                 print(f"⚠️ Flood control hit. Retry after {e.timeout}s.")
#                 await asyncio.sleep(e.timeout)
#                 message_ids = await send_images(bot, CHANNEL_ID, image_urls, caption)
#         else:
#             msg = await bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode="HTML")
#             message_ids = [msg.message_id]

#         # Step 4: Save all sent message IDs
#         if message_ids:
#             await save_message_ids(product_id, message_ids)

#         print("✅ Product post sent successfully.")

#     finally:
#         await bot.session.close()
#         print("✅ Bot session closed safely.")


# if __name__ == "__main__":
#     asyncio.run(send_test_message())
import asyncio
import aiosqlite
import re
from aiogram import Bot, types
from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
from config import DB_NAME, BOT_TOKEN, CHANNEL_ID

CHECK_INTERVAL = 5  # seconds between watcher loops
DELAY_BETWEEN_PRODUCTS = 1.5  # seconds between sending each product
CONCURRENT_LIMIT = 1  # safest for SendMediaGroup-heavy posts
MAX_RETRIES = 3  # retry attempts for flood control


def clean_html(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'</?p>', '\n', text)
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<.*?>', '', text)
    return text.strip()


async def send_images(bot: Bot, chat_id: str, image_urls: list[str], caption: str):
    if len(image_urls) == 1:
        msg = await bot.send_photo(chat_id=chat_id, photo=image_urls[0], caption=caption, parse_mode="HTML")
        return [msg.message_id]
    else:
        media = [types.InputMediaPhoto(media=image_urls[0], caption=caption, parse_mode="HTML")]
        for url in image_urls[1:]:
            media.append(types.InputMediaPhoto(media=url))
        messages = await bot.send_media_group(chat_id=chat_id, media=media)
        return [m.message_id for m in messages]


async def delete_previous_messages(db: aiosqlite.Connection, bot: Bot, product_id: int):
    async with db.execute("SELECT message_id FROM product_messages WHERE product_id = ?", (product_id,)) as cur:
        rows = await cur.fetchall()

    for (msg_id,) in rows:
        try:
            await bot.delete_message(chat_id=CHANNEL_ID, message_id=msg_id)
            print(f"🗑️ Deleted message {msg_id}")
        except TelegramBadRequest:
            print(f"⚠️ Message {msg_id} could not be deleted (already removed).")

    await db.execute("DELETE FROM product_messages WHERE product_id = ?", (product_id,))
    await db.commit()


async def save_message_ids(db: aiosqlite.Connection, product_id: int, message_ids: list[int]):
    await db.executemany(
        "INSERT INTO product_messages (product_id, message_id) VALUES (?, ?)",
        [(product_id, mid) for mid in message_ids]
    )
    await db.commit()


async def get_products_to_update(db: aiosqlite.Connection):
    async with db.execute("SELECT id FROM products WHERE visible = 1 AND needs_update = 1") as cursor:
        rows = await cursor.fetchall()
        return [r[0] for r in rows]


async def mark_product_sent(db: aiosqlite.Connection, product_id: int):
    await db.execute("UPDATE products SET needs_update = 0 WHERE id = ?", (product_id,))
    await db.commit()


async def send_product(bot: Bot, db: aiosqlite.Connection, product_id: int):
    async with db.execute(
        "SELECT name, description, url FROM products WHERE id = ? AND visible = 1",
        (product_id,)
    ) as cursor:
        product = await cursor.fetchone()
        if not product:
            return
    name, description, url = product
    description = clean_html(description)

    async with db.execute(
        "SELECT image_url FROM product_images WHERE product_id = ?", (product_id,)
    ) as cursor:
        images = await cursor.fetchall()
        image_urls = [img[0] for img in images if img[0]]

    await delete_previous_messages(db, bot, product_id)

    caption = f"🛒 <b>{name}</b>\n\n{description}\n\n🔗 More info: {url}"
    message_ids = []

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if image_urls:
                message_ids = await send_images(bot, CHANNEL_ID, image_urls, caption)
            else:
                msg = await bot.send_message(chat_id=CHANNEL_ID, text=caption, parse_mode="HTML")
                message_ids = [msg.message_id]
            break  # success
        except TelegramRetryAfter as e:
            wait = getattr(e, "retry_after", 5)
            backoff = wait * attempt
            print(f"⚠️ Flood control hit for product {product_id}. Retry {attempt}/{MAX_RETRIES} after {backoff}s.")
            await asyncio.sleep(backoff)
        except Exception as e:
            print(f"⚠️ Unexpected error sending product {product_id}: {e}")
            return  # skip this product

    if message_ids:
        await save_message_ids(db, product_id, message_ids)
        await mark_product_sent(db, product_id)
        print(f"✅ Product {product_id} posted.")

    await asyncio.sleep(DELAY_BETWEEN_PRODUCTS)


async def watch_products(bot: Bot):
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    async with aiosqlite.connect(DB_NAME) as db:
        while True:
            try:
                product_ids = await get_products_to_update(db)
                if product_ids:
                    async def sem_task(pid):
                        async with semaphore:
                            await send_product(bot, db, pid)
                    await asyncio.gather(*(sem_task(pid) for pid in product_ids))
                else:
                    print("⏱️ No updates found.")
            except Exception as e:
                print(f"⚠️ Error in watcher loop: {e}")
            await asyncio.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    bot = Bot(token=BOT_TOKEN)
    try:
        asyncio.run(watch_products(bot))
    except KeyboardInterrupt:
        print("🛑 Bot stopped manually.")
    finally:
        asyncio.run(bot.session.close())
        print("✅ Bot session closed safely.")
