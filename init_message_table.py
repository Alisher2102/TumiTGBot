import asyncio
import aiosqlite
from config import DB_NAME

async def init():
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS product_messages (
                product_id INTEGER,
                message_id INTEGER
            );
        """)
        await db.commit()
        print("✅ Table 'product_messages' created or already exists.")

if __name__ == "__main__":
    asyncio.run(init())
