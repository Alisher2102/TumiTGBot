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
import logging
from logging.handlers import RotatingFileHandler

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

# --- Logging Setup ---

# Formatter
formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")

# General bot logger — INFO and above
bot_logger = logging.getLogger("bot")
bot_logger.setLevel(logging.INFO)

bot_handler = RotatingFileHandler(
    filename="bot.log",
    maxBytes=2 * 1024 * 1024,
    backupCount=5,
    encoding="utf-8"
)
bot_handler.setFormatter(formatter)
bot_logger.addHandler(bot_handler)

# Error logger — WARNING and above
error_logger = logging.getLogger("errors")
error_logger.setLevel(logging.WARNING)

error_handler = RotatingFileHandler(
    filename="errors.log",
    maxBytes=2 * 1024 * 1024,
    backupCount=3,
    encoding="utf-8"
)
error_handler.setFormatter(formatter)
error_logger.addHandler(error_handler)

# ✅ Critical line: prevent error logs from going to bot.log
error_logger.propagate = False

# Console output
console = logging.StreamHandler()
console.setFormatter(formatter)
bot_logger.addHandler(console)
error_logger.addHandler(console)

# --- Test ---
# bot_logger.info("INFO: bot logger working")
# error_logger.error("ERROR: error logger working")



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
            bot_logger.info(f"Deleted message {msg_id} for product {product_id}")
        except TelegramBadRequest:
            print(f"⚠️ Message {msg_id} could not be deleted (already removed).")
            error_logger.warning(f"Failed to delete message {msg_id} for product {product_id}")


    await db.execute("DELETE FROM product_messages WHERE product_id = ?", (product_id,))
    await db.commit()

async def delete_out_of_stock(bot: Bot, db: aiosqlite.Connection, product_id: int):
    """ Deletes Telegram messages when stock is gone """
    print(f"🚫 Product {product_id} is OUT OF STOCK — removing posts...")
    bot_logger.info(f"Product {product_id} OUT OF STOCK — deleting messages")

    await delete_previous_messages(db, bot, product_id)

    # Optional: hide it from further processing
    # await db.execute("UPDATE products SET needs_update = 0 WHERE id = ?", (product_id,))
    # await db.commit()


async def save_message_ids(db: aiosqlite.Connection, product_id: int, message_ids: list[int]):
    await db.executemany(
        "INSERT INTO product_messages (product_id, message_id) VALUES (?, ?)",
        [(product_id, mid) for mid in message_ids]
    )
    await db.commit()


# async def get_products_to_update(db: aiosqlite.Connection):
#     async with db.execute("SELECT id FROM products WHERE visible = 1 AND needs_update = 1") as cursor:
#         rows = await cursor.fetchall()
#         return [r[0] for r in rows]

async def get_products_to_update(db: aiosqlite.Connection):
    async with db.execute("""
        SELECT DISTINCT product_id
        FROM product_messages
    """) as cursor:
        rows = await cursor.fetchall()

    update_list = []
    delete_list = []

    for (product_id,) in rows:
        async with db.execute("""
            SELECT stock, needs_update
            FROM products
            WHERE id = ? AND visible = 1
        """, (product_id,)) as cur:
            result = await cur.fetchone()

        if not result:
            continue

        stock, needs_update = result

        if stock is None or stock == 0:
            delete_list.append(product_id)
        elif needs_update == 1:
            update_list.append(product_id)

    return update_list, delete_list



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
            error_logger(f"⚠️ Flood control hit for product {product_id}. Retry {attempt}/{MAX_RETRIES} after {backoff}s.")
            await asyncio.sleep(backoff)
        except Exception as e:
            print(f"⚠️ Unexpected error sending product {product_id}: {e}")
            error_logger(f"⚠️ Unexpected error sending product {product_id}: {e}")
            return  # skip this product

    if message_ids:
        await save_message_ids(db, product_id, message_ids)
        await mark_product_sent(db, product_id)
        print(f"✅ Product {product_id} posted.")
        bot_logger.info(f"Product {product_id} posted.")

    await asyncio.sleep(DELAY_BETWEEN_PRODUCTS)


async def watch_products(bot: Bot):
    semaphore = asyncio.Semaphore(CONCURRENT_LIMIT)
    async with aiosqlite.connect(DB_NAME) as db:
        while True:
            try:
                update_list, delete_list = await get_products_to_update(db)
                # ⭐ Delete products that are OUT OF STOCK
                for pid in delete_list:
                    await delete_out_of_stock(bot, db, pid)

                # Process normal updates
                if update_list:
                    async def sem_task(pid):
                        async with semaphore:
                            await send_product(bot, db, pid)
                    await asyncio.gather(*(sem_task(pid) for pid in update_list))
                else:
                    print("⏱️ No updates found.")

            except Exception as e:
                print(f"⚠️ Error in watcher loop: {e}")
                error_logger(f"⚠️ Error in watcher loop: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

if __name__ == "__main__":

    bot = Bot(token=BOT_TOKEN)
    async def main():
    # ensures session closes even after crash / KeyboardInterrupt
        async with bot:
            while True:
                try:
                    bot_logger.info("Starting watcher loop...")
                    await watch_products(bot)
                except KeyboardInterrupt:
                    bot_logger.info("Bot stopped manually.")
                    break
                except Exception as e:
                    error_logger.exception(f"Bot crashed: {e}. Restarting in 10s...")
                    await asyncio.sleep(10)
                else:
                    bot_logger.warning("Watcher exited unexpectedly. Restarting in 5s...")
                    await asyncio.sleep(5)

    asyncio.run(main())
